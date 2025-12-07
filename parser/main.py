import logging
import argparse
import os
from logging.handlers import RotatingFileHandler
from pymongo import MongoClient

from .config import get_settings
from .api import OKAuth, OKApiClient
from .repositories import GroupRepository, CommentRepository, DiscussionRepository
from .services import ParserService

# Настройка логирования в файл
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "parser.log")

file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Консольный handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_formatter)

# Настройка root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")


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
    if not args.group_id.strip().isdigit():
        logger.error(f"Invalid group_id: {args.group_id}. Must contain only digits.")
        return
    
    service = create_parser_service()
    
    if args.discussion_id:
        count = service.parse_discussion(
            discussion_id=args.discussion_id,
            group_id=args.group_id,
        )
        logger.info(f"Parsed {count} comments")
    else:
        result = service.full_parse(
            group_id=args.group_id,
            max_discussions=args.max_discussions,
        )
        logger.info(f"Result: {result}")


if __name__ == "__main__":
    main()

