from typing import List, Dict, Optional, Any
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database

async def get_question_by_id(db: Database, question_id: str) -> Dict:
    """
    Retrieve a question by its ID.
    """
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(question_id)
        question = await db.questions.find_one({"_id": object_id})
        return question
    except Exception as e:
        print(f"Error retrieving question: {e}")
        return None

async def get_next_questions(
    db: Database, 
    user_id: str,
    count: int = 3,
    difficulty: Optional[str] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    user_progress: Optional[Dict] = None
) -> List[Dict]:
    """
    Get the next stack of questions for a user based on filters and adaptive learning.
    """
    # Build the query based on provided filters
    query = {}
    
    if difficulty:
        query["difficulty"] = difficulty
    if subject:
        query["subject"] = subject
    if topic:
        query["topic"] = topic
    
    # Exclude questions the user has already answered correctly
    if user_progress and "completed_questions" in user_progress:
        query["_id"] = {"$nin": [ObjectId(q_id) for q_id in user_progress["completed_questions"]]}
    
    # Sort by priority if available, otherwise use default order
    sort_criteria = [("priority", 1)]
    
    # If we have user progress data, we can do more sophisticated adaptive selection
    if user_progress and "skills" in user_progress:
        # Identify user's weakest skills
        weak_skills = sorted(
            user_progress["skills"].items(), 
            key=lambda x: x[1]["mastery_level"]
        )
        
        if weak_skills:
            # Add questions related to weak skills with higher priority
            weakest_skill = weak_skills[0][0]
            query["skills"] = weakest_skill
            
    # Find questions matching criteria
    cursor = db.questions.find(query).sort(sort_criteria).limit(count)
    questions = await cursor.to_list(length=count)
    
    # If we don't have enough questions, remove some filters and try again
    if len(questions) < count:
        # Remove topic filter if it exists
        if "topic" in query:
            del query["topic"]
            cursor = db.questions.find(query).sort(sort_criteria).limit(count - len(questions))
            additional_questions = await cursor.to_list(length=count - len(questions))
            questions.extend(additional_questions)
    
    # If we still don't have enough questions, get random ones
    if len(questions) < count:
        # Ensure we don't get duplicates
        existing_ids = [q["_id"] for q in questions]
        random_query = {"_id": {"$nin": existing_ids}}
        
        if user_progress and "completed_questions" in user_progress:
            random_query["_id"]["$nin"].extend([ObjectId(q_id) for q_id in user_progress["completed_questions"]])
            
        cursor = db.questions.find(random_query).limit(count - len(questions))
        additional_questions = await cursor.to_list(length=count - len(questions))
        questions.extend(additional_questions)
    
    return questions

async def save_user_answer(
    db: Database,
    user_id: str,
    question_id: str,
    user_answer: Any,
    time_taken: float = 0
) -> Dict:
    """
    Save the user's answer to a question and evaluate it.
    """
    try:
        # Convert string IDs to ObjectIds
        user_object_id = ObjectId(user_id)
        question_object_id = ObjectId(question_id)
        
        # Get the question to check the answer
        question = await db.questions.find_one({"_id": question_object_id})
        if not question:
            raise ValueError("Question not found")
            
        # Determine if the answer is correct
        is_correct = False
        feedback = "Incorrect answer."
        score = 0
        
        # Check based on question type
        question_type = question.get("type", "multiple_choice")
        
        if question_type == "multiple_choice":
            correct_answer = question.get("correct_answer")
            is_correct = user_answer == correct_answer
            if is_correct:
                feedback = "Correct!"
                score = question.get("points", 10)
            else:
                feedback = question.get("explanations", {}).get(str(user_answer), "Incorrect choice.")
                
        elif question_type == "text":
            # For text answers, we might need more sophisticated comparison
            correct_answer = question.get("correct_answer", "").lower().strip()
            user_text = str(user_answer).lower().strip()
            is_correct = user_text == correct_answer
            if is_correct:
                feedback = "Correct!"
                score = question.get("points", 10)
            else:
                feedback = question.get("explanation", "Incorrect answer.")
                
        # Create answer record
        answer_record = {
            "user_id": user_object_id,
            "question_id": question_object_id,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "time_taken": time_taken,
            "score": score,
            "timestamp": datetime.utcnow()
        }
        
        # Save the answer to the database
        await db.user_answers.insert_one(answer_record)
        
        # Update user progress
        await update_user_progress(
            db, 
            user_id=user_id, 
            question_id=question_id,
            question=question,
            is_correct=is_correct
        )
        
        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "score": score
        }
    except Exception as e:
        print(f"Error saving user answer: {e}")
        raise

async def update_user_progress(
    db: Database,
    user_id: str,
    question_id: str,
    question: Dict,
    is_correct: bool
) -> None:
    """
    Update the user's progress based on their answer.
    """
    user_object_id = ObjectId(user_id)
    
    # Get or create user progress document
    progress = await db.user_progress.find_one({"user_id": user_object_id})
    
    if not progress:
        # Initialize new progress record
        progress = {
            "user_id": user_object_id,
            "completed_questions": [],
            "attempted_questions": [],
            "correct_answers": 0,
            "total_attempts": 0,
            "skills": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    # Update progress data
    progress["total_attempts"] += 1
    
    if question_id not in progress["attempted_questions"]:
        progress["attempted_questions"].append(question_id)
    
    if is_correct:
        progress["correct_answers"] += 1
        if question_id not in progress["completed_questions"]:
            progress["completed_questions"].append(question_id)
    
    # Update skills mastery
    skills = question.get("skills", [])
    for skill in skills:
        if skill not in progress["skills"]:
            progress["skills"][skill] = {
                "mastery_level": 0,
                "attempts": 0,
                "correct": 0
            }
        
        progress["skills"][skill]["attempts"] += 1
        if is_correct:
            progress["skills"][skill]["correct"] += 1
            
        # Recalculate mastery level (0-100%)
        attempts = progress["skills"][skill]["attempts"]
        correct = progress["skills"][skill]["correct"]
        if attempts > 0:
            mastery = (correct / attempts) * 100
            # Apply forgetting curve effect
            decay_factor = 0.9  # Simple decay factor
            old_mastery = progress["skills"][skill]["mastery_level"]
            new_mastery = (old_mastery * decay_factor) + (mastery * (1 - decay_factor))
            progress["skills"][skill]["mastery_level"] = new_mastery
    
    progress["updated_at"] = datetime.utcnow()
    
    # Update or insert the progress document
    await db.user_progress.update_one(
        {"user_id": user_object_id}, 
        {"$set": progress}, 
        upsert=True
    )

async def get_user_progress(db: Database, user_id: str) -> Dict:
    """
    Get the user's learning progress.
    """
    user_object_id = ObjectId(user_id)
    progress = await db.user_progress.find_one({"user_id": user_object_id})
    
    if not progress:
        # Initialize default progress
        progress = {
            "user_id": user_object_id,
            "completed_questions": [],
            "attempted_questions": [],
            "correct_answers": 0,
            "total_attempts": 0,
            "skills": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.user_progress.insert_one(progress)
    
    return progress

async def calculate_user_performance(db: Database, user_id: str) -> Dict:
    """
    Calculate user performance metrics.
    """
    progress = await get_user_progress(db, user_id)
    
    # Calculate basic metrics
    total_attempts = progress.get("total_attempts", 0)
    correct_answers = progress.get("correct_answers", 0)
    accuracy = 0
    if total_attempts > 0:
        accuracy = (correct_answers / total_attempts) * 100
    
    # Get skill strengths and weaknesses
    skills = progress.get("skills", {})
    skill_levels = []
    
    for skill, data in skills.items():
        skill_levels.append({
            "skill": skill,
            "mastery_level": data.get("mastery_level", 0),
            "attempts": data.get("attempts", 0)
        })
    
    # Sort by mastery level
    skill_levels.sort(key=lambda x: x["mastery_level"])
    
    strengths = skill_levels[-3:] if len(skill_levels) > 3 else skill_levels
    weaknesses = skill_levels[:3] if len(skill_levels) > 0 else []
    
    return {
        "accuracy": accuracy,
        "total_questions_attempted": total_attempts,
        "unique_questions_completed": len(progress.get("completed_questions", [])),
        "unique_questions_attempted": len(progress.get("attempted_questions", [])),
        "strengths": strengths,
        "weaknesses": weaknesses
    }

async def recommend_next_question(
    db: Database,
    user_id: str,
    current_question_id: str,
    result: Dict
) -> str:
    """
    Recommend the next question based on the user's performance.
    """
    # Get the current question to access related topics/skills
    question = await get_question_by_id(db, current_question_id)
    if not question:
        # If question not found, return None
        return None
    
    # Get user progress
    progress = await get_user_progress(db, user_id)
    
    # Recommendation strategy based on answer correctness
    if result["is_correct"]:
        # If correct, advance to a slightly harder question on the same topic
        query = {
            "topic": question.get("topic"),
            "difficulty": {"$gt": question.get("difficulty", "medium")},
            "_id": {"$ne": ObjectId(current_question_id)}
        }
        
        # Exclude completed questions
        if "completed_questions" in progress and progress["completed_questions"]:
            query["_id"]["$nin"] = [ObjectId(q_id) for q_id in progress["completed_questions"]]
    else:
        # If incorrect, find a similar or slightly easier question on the same topic/skill
        query = {
            "topic": question.get("topic"),
            "difficulty": {"$lte": question.get("difficulty", "medium")},
            "_id": {"$ne": ObjectId(current_question_id)}
        }
        
        # Target the specific skills the user got wrong
        if "skills" in question:
            query["skills"] = {"$in": question.get("skills", [])}
    
    # Find a matching question
    next_question = await db.questions.find_one(query)
    
    # If no matching question found, get any unanswered question
    if not next_question:
        basic_query = {"_id": {"$ne": ObjectId(current_question_id)}}
        if "completed_questions" in progress and progress["completed_questions"]:
            basic_query["_id"]["$nin"] = [ObjectId(q_id) for q_id in progress["completed_questions"]]
        
        next_question = await db.questions.find_one(basic_query)
    
    return str(next_question["_id"]) if next_question else None

def format_question_response(question: Dict) -> Dict:
    """
    Format a question for API response, removing sensitive fields like correct answers.
    """
    if not question:
        return {}
    
    # Clone the question to avoid modifying the original
    response = dict(question)
    
    # Convert ObjectId to string
    response["_id"] = str(response["_id"])
    
    # Remove answers for client-side response
    if "correct_answer" in response:
        del response["correct_answer"]
    
    if "explanations" in response:
        del response["explanations"]
    
    # Keep other fields like question text, options, difficulty, etc.
    
    return response