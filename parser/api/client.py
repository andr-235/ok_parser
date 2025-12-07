import time
import logging
from typing import Any, Optional

import requests

from .base import BaseAPI
from .auth import OKAuth
from ..models import Group, Comment

logger = logging.getLogger(__name__)


class OKApiError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"OK API Error {code}: {message}")


class OKApiClient(BaseAPI):
    def __init__(
        self,
        auth: OKAuth,
        base_url: str = "https://api.ok.ru/fb.do",
        rate_limit_delay: float = 1.0,
    ):
        self._auth = auth
        self._base_url = base_url
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0

    def _wait_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

    def request(
        self,
        method: str,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        self._wait_rate_limit()
        
        request_params = params.copy() if params else {}
        request_params["method"] = method
        request_params["format"] = "json"
        
        signed_params = self._auth.sign_params(request_params)
        
        try:
            response = requests.get(self._base_url, params=signed_params, timeout=30)
            response.raise_for_status()
            self._last_request_time = time.time()
            
            logger.debug(f"Response status: {response.status_code}, length: {len(response.text)}")
            
            data = response.json()
            
            if data is None:
                logger.error(f"Empty response from API")
                return None
            
            if "error_code" in data:
                raise OKApiError(
                    code=data.get("error_code", 0),
                    message=data.get("error_msg", "Unknown error"),
                )
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_group_info(self, group_id: str, fields: Optional[str] = None) -> Group:
        # Валидация group_id
        if not group_id or not str(group_id).strip().isdigit():
            raise ValueError(f"Invalid group_id: {group_id}. Must contain only digits.")
        
        params = {"uids": str(group_id).strip()}
        if fields:
            params["fields"] = fields
        else:
            params["fields"] = "uid,name,description,members_count,pic_avatar"
        
        response = self.request("group.getInfo", params)
        
        if response is None:
            raise ValueError(f"Group {group_id} not found")
        
        groups = response if isinstance(response, list) else [response]
        if not groups or groups[0] is None:
            raise ValueError(f"Group {group_id} not found")
        
        return Group.from_api(groups[0])

    def get_comments(
        self,
        discussion_id: str,
        group_id: str,
        discussion_type: str = "GROUP_TOPIC",
        count: int = 100,
        offset: int = 0,
        sort_order: str = "LAST",
        discussion_text: Optional[str] = None,
    ) -> list[Comment]:
        # Валидация входных данных
        if not discussion_id or not str(discussion_id).strip():
            raise ValueError("discussion_id cannot be empty")
        if not group_id or not str(group_id).strip().isdigit():
            raise ValueError(f"Invalid group_id: {group_id}. Must contain only digits.")
        if count < 1 or count > 1000:
            raise ValueError(f"count must be between 1 and 1000, got {count}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        
        params = {
            "discussionId": str(discussion_id).strip(),
            "discussionType": discussion_type,
            "count": str(count),
            "offset": str(offset),
            "order": sort_order,
        }
        
        response = self.request("discussions.getComments", params)
        
        logger.info(
            f"get_comments: discussionId={discussion_id}, "
            f"discussionType={discussion_type}, group_id={group_id}"
        )
        
        if response is None:
            logger.warning(f"No response for discussion {discussion_id}")
            return []
        comments_data = response.get("comments", [])
        logger.info(f"Got {len(comments_data)} comments from API response")
        
        author_ids = list(set(
            str(c.get("author_id", ""))
            for c in comments_data
            if c.get("author_id")
        ))
        
        users_map = self.get_users_info(author_ids)
        
        return [
            Comment.from_api(
                c,
                discussion_id,
                group_id,
                users_map.get(str(c.get("author_id", "")), {}),
                discussion_text,
            )
            for c in comments_data
        ]

    def get_discussions(
        self,
        group_id: str,
        count: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        # Валидация входных данных
        if not group_id or not str(group_id).strip().isdigit():
            raise ValueError(f"Invalid group_id: {group_id}. Must contain only digits.")
        if count < 1 or count > 1000:
            raise ValueError(f"count must be between 1 and 1000, got {count}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        
        all_discussions = []
        
        # Получаем обсуждения через discussions.getList
        # ВАЖНО: API возвращает активность В группе (посты пользователей),
        # а не официальные посты ОТ группы. Для постов группы нужны права админа.
        params_list = {
            "gid": str(group_id).strip(),
            "count": str(count),
            "offset": str(offset),
        }
        
        logger.info(f"get_discussions: fetching discussions from group {group_id}, params={params_list}")
        response_list = self.request("discussions.getList", params_list)
        
        logger.info(f"get_discussions.getList response type: {type(response_list)}")
        logger.info(f"get_discussions.getList response keys: {list(response_list.keys()) if isinstance(response_list, dict) else 'Not a dict'}")
        logger.info(f"get_discussions.getList full response (first 500 chars): {str(response_list)[:500]}")
        
        if response_list is None:
            logger.warning("get_discussions: discussions.getList response is None")
        else:
            # discussions.getList возвращает discussions или topics
            discussions = []
            if isinstance(response_list, dict):
                discussions = response_list.get("discussions", response_list.get("topics", []))
            elif isinstance(response_list, list):
                discussions = response_list
            
            if isinstance(discussions, list):
                # API discussions.getList возвращает активность в группе
                # Это посты пользователей (owner_uid != group_id), а не официальные посты группы
                # Собираем все обсуждения, т.к. это максимум доступного без прав админа
                for d in discussions:
                    if not d:
                        continue
                    owner_uid = d.get("owner_uid")
                    object_type = d.get("object_type", "")
                    object_id = d.get("object_id", "")
                    
                    all_discussions.append(d)
                    
                    # Логируем, если найден пост от группы (редкость)
                    if owner_uid and str(owner_uid) == str(group_id):
                        logger.info(f"get_discussions: found GROUP post {object_id} (type={object_type})")
                    else:
                        logger.debug(f"get_discussions: user post {object_id} (type={object_type}, owner={owner_uid})")
                
                logger.info(f"get_discussions: collected {len(all_discussions)} discussions from group feed")
            else:
                logger.warning(f"get_discussions: discussions from getList is not a list: {type(discussions)}")
        
        logger.info(f"get_discussions: total {len(all_discussions)} discussions for group {group_id}")
        
        # Логируем типы обсуждений
        if all_discussions:
            types_count = {}
            for d in all_discussions:
                if d:
                    t = d.get('object_type', 'UNKNOWN')
                    types_count[t] = types_count.get(t, 0) + 1
            logger.info(f"get_discussions: discussion types: {types_count}")
        
        return all_discussions
    
    def get_users_info(self, user_ids: list[str]) -> dict[str, dict]:
        if not user_ids:
            return {}
        
        # Валидация и очистка user_ids
        valid_ids = [str(uid).strip() for uid in user_ids if uid and str(uid).strip().isdigit()]
        if not valid_ids:
            return {}
        
        # Ограничение количества для предотвращения слишком больших запросов
        if len(valid_ids) > 100:
            logger.warning(f"Too many user_ids ({len(valid_ids)}), limiting to 100")
            valid_ids = valid_ids[:100]
        
        params = {
            "uids": ",".join(valid_ids),
            "fields": "uid,first_name,last_name,name",
        }
        
        response = self.request("users.getInfo", params)
        if response is None:
            return {}
        
        users = response if isinstance(response, list) else [response]
        return {str(u.get("uid", "")): u for u in users if u.get("uid")}

