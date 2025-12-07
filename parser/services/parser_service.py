import logging
from typing import Optional

from ..api import OKApiClient
from ..models import Group, Comment, Discussion
from ..repositories import GroupRepository, CommentRepository, DiscussionRepository

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
            logger.info(f"  -> Discussion text: {discussion_text[:100] if discussion_text else 'None'}")
        
        comments = self._api.get_comments(
            discussion_id=discussion_id,
            group_id=group_id,
            discussion_type=discussion_type,
            count=count,
            discussion_text=discussion_text,
        )
        
        logger.info(f"  -> Got {len(comments)} comments from API")
        
        if not comments:
            logger.info(f"  -> No comments found for discussion {discussion_id}")
            return 0
        
        logger.info(f"  -> Saving comments with group_id={group_id}")
        for i, comment in enumerate(comments[:3], 1):
            logger.info(
                f"  -> Comment #{i}: author={comment.author_name}, "
                f"discussion_id={comment.discussion_id}, group_id={comment.group_id}"
            )
        
        saved = self._comment_repo.upsert_many(comments)
        logger.info(f"  -> Saved {saved} comments to DB (group_id={group_id})")
        return saved

    def parse_all_discussions(
        self,
        group_id: str,
        max_discussions: Optional[int] = None,
        comments_per_discussion: int = 100,
    ) -> tuple[int, int]:
        logger.info(f"Parsing all discussions for group {group_id}")
        
        discussions = self._api.get_discussions(group_id)
        
        logger.info(f"API returned {len(discussions) if discussions else 0} discussions")
        
        if discussions:
            types_count = {}
            for d in discussions:
                if d:
                    t = d.get('object_type', 'UNKNOWN')
                    types_count[t] = types_count.get(t, 0) + 1
            logger.info(f"Discussion types from API: {types_count}")
        
        if not discussions:
            logger.info("No discussions found")
            return 0, 0
        
        logger.info(f"Searching for discussion 158991371972782 in {len(discussions)} discussions")
        target_found = False
        target_position = None
        for idx, d in enumerate(discussions):
            if d and str(d.get('object_id', '')) == '158991371972782':
                logger.info(f"FOUND target discussion at position {idx+1}: type={d.get('object_type')}, owner={d.get('owner_uid')}, full_data={d}")
                target_found = True
                target_position = idx + 1
        
        if not target_found:
            logger.warning(
                f"Target discussion 158991371972782 NOT FOUND in {len(discussions)} discussions! "
                f"This discussion exists (GROUP_TOPIC) but API discussions.getList doesn't return it. "
                f"This may mean API doesn't return all group discussions."
            )
        
        if max_discussions:
            if target_found and target_position and target_position > max_discussions:
                logger.warning(
                    f"Target discussion is at position {target_position}, "
                    f"but max_discussions={max_discussions} will skip it!"
                )
            logger.info(f"Limiting to {max_discussions} discussions (will skip discussions after position {max_discussions})")
            original_count = len(discussions)
            discussions = discussions[:max_discussions]
            logger.info(f"Limited from {original_count} to {len(discussions)} discussions")
        
        total_comments = 0
        parsed_discussions = 0
        skipped_count = 0
        
        for idx, discussion in enumerate(discussions, 1):
            if discussion is None:
                logger.warning(f"Discussion #{idx} is None, skipping")
                continue
            
            discussion_type = discussion.get("object_type", "GROUP_TOPIC")
            owner_uid = discussion.get("owner_uid")
            discussion_id = str(discussion.get("object_id", discussion.get("id", "")))
            title = discussion.get("title", "")[:50] if discussion.get("title") else ""
            
            logger.info(
                f"[{idx}/{len(discussions)}] Discussion ID: {discussion_id}, "
                f"Type: {discussion_type}, Owner: {owner_uid}, "
                f"Title: {title}, Group ID: {group_id}"
            )
            
            if not discussion_id:
                logger.warning(f"Discussion #{idx} has no ID, skipping")
                continue
            
            # API discussions.getList уже фильтрует по группе (gid)
            # Все обсуждения, которые возвращает API, относятся к этой группе
            # Поэтому парсим все, что возвращает API
            # GROUP_TOPIC - это темы форума группы (могут отсутствовать)
            # USER_STATUS, USER_PHOTO, MOVIE - это посты из ленты группы
            is_group_discussion = True
            
            logger.info(
                f"  -> Is group discussion: {is_group_discussion} "
                f"(type={discussion_type}, owner={owner_uid}, group={group_id})"
            )
            
            if not is_group_discussion:
                skipped_count += 1
                logger.info(
                    f"  -> SKIPPING {discussion_type} (owner: {owner_uid}) - "
                    f"not a group discussion"
                )
                continue
            
            try:
                logger.info(f"  -> Processing discussion {discussion_id}")
                discussion_obj = Discussion.from_api(discussion, group_id)
                self._discussion_repo.upsert(discussion_obj)
                logger.info(f"  -> Saved discussion to DB with group_id: {discussion_obj.group_id}")
                
                count = self.parse_discussion(
                    discussion_id=discussion_id,
                    group_id=group_id,
                    discussion_type=discussion_type,
                    count=comments_per_discussion,
                    discussion_data=discussion,
                )
                logger.info(f"  -> Parsed {count} comments from discussion {discussion_id}")
                total_comments += count
                parsed_discussions += 1
            except Exception as e:
                logger.error(f"  -> ERROR: Failed to parse discussion {discussion_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
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

