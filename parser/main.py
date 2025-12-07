import logging
import argparse
import os
from pymongo import MongoClient

from .config import get_settings
from .api import OKAuth, OKApiClient
from .repositories import GroupRepository, CommentRepository, DiscussionRepository
from .services import ParserService
from .utils.logging import setup_logging
from .utils.validation import validate_group_id

# Настройка логирования
log_file = os.path.join("logs", "parser.log")
setup_logging(log_file)
logger = logging.getLogger(__name__)


def create_parser_service() -> ParserService:
    settings = get_settings()
    
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    
    auth = OKAuth(
        client_id=settings.ok_client_id,
        client_secret=settings.ok_client_secret,
        access_token=settings.ok_access_token,
        public_key=settings.ok_public_key,
        session_key=settings.ok_session_key,
        session_secret_key=settings.ok_session_secret_key,
    )
    
    api = OKApiClient(
        auth=auth,
        base_url=settings.api_base_url,
        rate_limit_delay=settings.rate_limit_delay,
    )
    
    group_repo = GroupRepository(db)
    comment_repo = CommentRepository(db)
    discussion_repo = DiscussionRepository(db)
    
    return ParserService(
        api=api,
        group_repo=group_repo,
        comment_repo=comment_repo,
        discussion_repo=discussion_repo,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="OK Parser")
    parser.add_argument("group_id", help="Group ID to parse")
    parser.add_argument(
        "--max-discussions",
        type=int,
        default=None,
        help="Max discussions to parse",
    )
    parser.add_argument(
        "--discussion-id",
        help="Parse single discussion",
    )
    args = parser.parse_args()
    
    # Валидация group_id
    try:
        group_id = validate_group_id(args.group_id)
    except ValueError as e:
        logger.error(str(e))
        return
    
    service = create_parser_service()
    
    if args.discussion_id:
        count = service.parse_discussion(
            discussion_id=args.discussion_id,
            group_id=group_id,
        )
        logger.info(f"Parsed {count} comments")
    else:
        result = service.full_parse(
            group_id=group_id,
            max_discussions=args.max_discussions,
        )
        logger.info(f"Result: {result}")


if __name__ == "__main__":
    main()

