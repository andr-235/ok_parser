import logging
from typing import Optional

from ..api import OKApiClient
from ..models import Group, Comment, Discussion
from ..repositories import GroupRepository, CommentRepository, DiscussionRepository
from ..utils.validation import validate_group_id

logger = logging.getLogger(__name__)


class ParserService:
    def __init__(
        self,
        api: OKApiClient,
        group_repo: GroupRepository,
        comment_repo: CommentRepository,
        discussion_repo: DiscussionRepository,
    ):
        self._api = api
        self._group_repo = group_repo
        self._comment_repo = comment_repo
        self._discussion_repo = discussion_repo

    def parse_group(self, group_id: str) -> Group:
        group_id = validate_group_id(group_id)
        logger.info(f"Parsing group {group_id}")
        group = self._api.get_group_info(group_id)
        self._group_repo.upsert(group)
        logger.info(f"Group {group.name} saved")
        return group

    def parse_discussion(
        self,
        discussion_id: str,
        group_id: str,
        discussion_type: str = "GROUP_TOPIC",
        count: int = 100,
        discussion_data: Optional[dict] = None,
    ) -> int:
        # Валидация входных данных
        if not discussion_id or not str(discussion_id).strip():
            raise ValueError("discussion_id cannot be empty")
        group_id = validate_group_id(group_id)
        if count < 1 or count > 1000:
            raise ValueError(f"count must be between 1 and 1000, got {count}")
        
        logger.info(
            f"Parsing discussion {discussion_id} ({discussion_type}) "
            f"for group {group_id}"
        )
        
        discussion_text = None
        if discussion_data:
            title = discussion_data.get("title")
            message = discussion_data.get("message")
            parts = []
            if title:
                parts.append(title)
            if message:
                parts.append(message)
            discussion_text = " | ".join(parts) if parts else None
        
        comments = self._api.get_comments(
            discussion_id=discussion_id,
            group_id=group_id,
            discussion_type=discussion_type,
            count=count,
            discussion_text=discussion_text,
        )
        
        if not comments:
            logger.debug(f"No comments found for discussion {discussion_id}")
            return 0
        
        saved = self._comment_repo.upsert_many(comments)
        logger.info(f"Saved {saved} comments from discussion {discussion_id}")
        return saved

    def _log_discussion_types(self, discussions: list[dict]) -> None:
        """Логирование типов обсуждений."""
        if not discussions:
            return
        
        types_count = {}
        for d in discussions:
            if d:
                t = d.get('object_type', 'UNKNOWN')
                types_count[t] = types_count.get(t, 0) + 1
        logger.info(f"Discussion types from API: {types_count}")

    def _process_discussion(
        self,
        discussion: dict,
        group_id: str,
        idx: int,
        total: int,
        comments_per_discussion: int,
    ) -> tuple[bool, int]:
        """
        Обработка одного обсуждения.
        
        Returns:
            tuple[bool, int]: (успешно обработано, количество сохраненных комментариев)
        """
        if discussion is None:
            logger.warning(f"Discussion #{idx} is None, skipping")
            return False, 0
        
        discussion_type = discussion.get("object_type", "GROUP_TOPIC")
        owner_uid = discussion.get("owner_uid")
        discussion_id = str(discussion.get("object_id", discussion.get("id", "")))
        title = discussion.get("title", "")[:50] if discussion.get("title") else ""
        
        logger.debug(
            f"[{idx}/{total}] Discussion ID: {discussion_id}, "
            f"Type: {discussion_type}, Owner: {owner_uid}"
        )
        
        if not discussion_id:
            logger.warning(f"Discussion #{idx} has no ID, skipping")
            return False, 0
        
        # API discussions.getList уже фильтрует по группе (gid)
        # Все обсуждения, которые возвращает API, относятся к этой группе
        is_group_discussion = True
        
        if not is_group_discussion:
            logger.debug(f"Skipping {discussion_type} (owner: {owner_uid})")
            return False, 0
        
        try:
            discussion_obj = Discussion.from_api(discussion, group_id)
            self._discussion_repo.upsert(discussion_obj)
            
            count = self.parse_discussion(
                discussion_id=discussion_id,
                group_id=group_id,
                discussion_type=discussion_type,
                count=comments_per_discussion,
                discussion_data=discussion,
            )
            logger.debug(f"Parsed {count} comments from discussion {discussion_id}")
            return True, count
        except Exception as e:
            logger.error(f"  -> ERROR: Failed to parse discussion {discussion_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, 0

    def parse_all_discussions(
        self,
        group_id: str,
        max_discussions: Optional[int] = None,
        comments_per_discussion: int = 100,
    ) -> tuple[int, int]:
        logger.info(f"Parsing all discussions for group {group_id}")
        
        discussions = self._api.get_discussions(group_id)
        logger.info(f"API returned {len(discussions) if discussions else 0} discussions")
        
        self._log_discussion_types(discussions)
        
        if not discussions:
            logger.info("No discussions found")
            return 0, 0
        
        if max_discussions:
            logger.info(f"Limiting to {max_discussions} discussions")
            original_count = len(discussions)
            discussions = discussions[:max_discussions]
            logger.info(f"Limited from {original_count} to {len(discussions)} discussions")
        
        total_comments = 0
        parsed_discussions = 0
        skipped_count = 0
        
        for idx, discussion in enumerate(discussions, 1):
            success, count = self._process_discussion(
                discussion=discussion,
                group_id=group_id,
                idx=idx,
                total=len(discussions),
                comments_per_discussion=comments_per_discussion,
            )
            
            if success:
                total_comments += count
                parsed_discussions += 1
            else:
                skipped_count += 1
        
        logger.info(
            f"Summary: Total discussions from API: {len(discussions)}, "
            f"Parsed: {parsed_discussions}, Skipped: {skipped_count}, "
            f"Comments saved: {total_comments}"
        )
        return parsed_discussions, total_comments

    def full_parse(
        self,
        group_id: str,
        max_discussions: Optional[int] = None,
    ) -> dict:
        group = self.parse_group(group_id)
        discussions, comments = self.parse_all_discussions(
            group_id=group_id,
            max_discussions=max_discussions,
        )
        
        return {
            "group": group.name or group.uid,
            "discussions_parsed": discussions,
            "comments_saved": comments,
        }

