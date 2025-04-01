from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

# Import the database object directly instead of get_database function
from app.database import database, questions_collection
from app.qna.utils import (
    get_question_by_id,
    get_next_questions,
    save_user_answer,
    format_question_response,
    get_user_progress,
    recommend_next_question,
    calculate_user_performance
)
from app.auth.utils import get_current_user

router = APIRouter()

# Create a dependency function that returns the database
async def get_database():
    return database

@router.get("/questions/{question_id}", response_model=dict)
async def get_question(
    question_id: str,
    db: Database = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific question by ID.
    """
    try:
        question = await get_question_by_id(db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        return format_question_response(question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



@router.get("/questions/next/{count}", response_model=List[dict])
async def get_stack_of_questions(
    count: int = 3,
    difficulty: Optional[str] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    db: Database = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get next 'count' questions stacked for the user based on optional filters.
    Default is 3 questions.
    """
    if count < 1 or count > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Count must be between 1 and 10"
        )
    
    # Get user's progress to determine appropriate questions
    user_progress = await get_user_progress(db, current_user["_id"])
    
    # Get next questions based on user's progress and any filters
    questions = await get_next_questions(
        db, 
        user_id=current_user["_id"],
        count=count,
        difficulty=difficulty,
        subject=subject,
        topic=topic,
        user_progress=user_progress
    )
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions available with the specified criteria"
        )
    
    # Format questions for response
    formatted_questions = [format_question_response(q) for q in questions]
    return formatted_questions

@router.post("/questions/{question_id}/answer", response_model=dict)
async def submit_answer(
    question_id: str,
    answer_data: dict,
    db: Database = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Save user's answer to a question and return feedback/result.
    """
    try:
        # Verify the question exists
        question = await get_question_by_id(db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        # Save the user's answer
        result = await save_user_answer(
            db,
            user_id=current_user["_id"],
            question_id=question_id,
            user_answer=answer_data.get("answer"),
            time_taken=answer_data.get("time_taken", 0)
        )
        
        # Calculate user performance metrics
        performance = await calculate_user_performance(db, current_user["_id"])
        
        # Get recommendation for next question
        next_question_id = await recommend_next_question(
            db, 
            user_id=current_user["_id"],
            current_question_id=question_id,
            result=result
        )
        
        response = {
            "correct": result["is_correct"],
            "score": result["score"],
            "feedback": result["feedback"],
            "performance": performance,
            "next_question_id": next_question_id
        }
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/progress", response_model=dict)
async def get_learning_progress(
    db: Database = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the user's learning progress and statistics.
    """
    try:
        progress = await get_user_progress(db, current_user["_id"])
        performance = await calculate_user_performance(db, current_user["_id"])
        
        return {
            "progress": progress,
            "performance": performance
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )