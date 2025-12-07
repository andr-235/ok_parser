def validate_group_id(group_id: str) -> str:
    """
    Валидация group_id.
    
    Args:
        group_id: ID группы для валидации
    
    Returns:
        Очищенный и валидированный group_id
    
    Raises:
        ValueError: Если group_id невалиден
    """
    if not group_id or not str(group_id).strip().isdigit():
        raise ValueError(f"Invalid group_id: {group_id}. Must contain only digits.")
    return str(group_id).strip()

