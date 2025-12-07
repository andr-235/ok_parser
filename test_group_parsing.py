#!/usr/bin/env python3
"""
Скрипт для проверки парсинга разных групп.
Проверяет, что API возвращает разные обсуждения для разных групп,
а не личную ленту пользователя.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.config import get_settings
from parser.api import OKAuth, OKApiClient

load_dotenv()

def test_groups(group_ids: list[str]):
    """Тестирует парсинг нескольких групп и сравнивает результаты."""
    
    settings = get_settings()
    
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
    
    results = {}
    
    for group_id in group_ids:
        print(f"\n{'='*80}")
        print(f"Тестируем группу: {group_id}")
        print(f"{'='*80}")
        
        # Получаем информацию о группе
        try:
            group = api.get_group_info(group_id)
            print(f"Группа: {group.name}")
            print(f"Описание: {group.description[:100] if group.description else 'N/A'}...")
        except Exception as e:
            print(f"ОШИБКА получения информации о группе: {e}")
            continue
        
        # Получаем обсуждения
        try:
            discussions = api.get_discussions(group_id, count=10, offset=0)
            print(f"\nПолучено обсуждений: {len(discussions)}")
            
            if discussions:
                # Анализируем обсуждения
                owner_stats = {}
                type_stats = {}
                discussion_ids = []
                
                for d in discussions:
                    owner_uid = d.get("owner_uid", "unknown")
                    object_type = d.get("object_type", "unknown")
                    object_id = d.get("object_id", "unknown")
                    
                    owner_stats[owner_uid] = owner_stats.get(owner_uid, 0) + 1
                    type_stats[object_type] = type_stats.get(object_type, 0) + 1
                    discussion_ids.append(object_id)
                
                print(f"\nСтатистика по владельцам (owner_uid):")
                for owner, count in sorted(owner_stats.items(), key=lambda x: x[1], reverse=True):
                    is_group = "✓ ГРУППА" if str(owner) == str(group_id) else "✗ НЕ ГРУППА"
                    print(f"  {owner}: {count} обсуждений {is_group}")
                
                print(f"\nСтатистика по типам:")
                for dtype, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {dtype}: {count}")
                
                print(f"\nПервые 5 ID обсуждений:")
                for did in discussion_ids[:5]:
                    print(f"  {did}")
                
                results[group_id] = {
                    "group_name": group.name,
                    "discussion_ids": set(discussion_ids),
                    "owner_stats": owner_stats,
                    "type_stats": type_stats,
                    "count": len(discussions),
                }
            else:
                print("⚠ Обсуждений не найдено!")
                results[group_id] = {
                    "group_name": group.name,
                    "discussion_ids": set(),
                    "owner_stats": {},
                    "type_stats": {},
                    "count": 0,
                }
        except Exception as e:
            print(f"ОШИБКА получения обсуждений: {e}")
            import traceback
            traceback.print_exc()
            results[group_id] = None
    
    # Сравниваем результаты
    if len(results) >= 2:
        print(f"\n{'='*80}")
        print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
        print(f"{'='*80}")
        
        group_ids_list = [gid for gid in group_ids if results.get(gid)]
        if len(group_ids_list) >= 2:
            g1, g2 = group_ids_list[0], group_ids_list[1]
            r1, r2 = results[g1], results[g2]
            
            common_ids = r1["discussion_ids"] & r2["discussion_ids"]
            unique_to_g1 = r1["discussion_ids"] - r2["discussion_ids"]
            unique_to_g2 = r2["discussion_ids"] - r1["discussion_ids"]
            
            print(f"\nГруппа 1: {r1['group_name']} ({g1})")
            print(f"  Обсуждений: {r1['count']}")
            print(f"\nГруппа 2: {r2['group_name']} ({g2})")
            print(f"  Обсуждений: {r2['count']}")
            
            print(f"\nОбщих ID обсуждений: {len(common_ids)}")
            if common_ids:
                print("  ⚠ ВНИМАНИЕ: Найдены одинаковые обсуждения в разных группах!")
                print("  Это может означать, что API возвращает личную ленту пользователя.")
                print(f"  Общие ID (первые 10): {list(common_ids)[:10]}")
            else:
                print("  ✓ Общих обсуждений нет - это хорошо!")
            
            print(f"\nУникальных для группы 1: {len(unique_to_g1)}")
            print(f"Уникальных для группы 2: {len(unique_to_g2)}")
            
            if len(common_ids) > len(r1["discussion_ids"]) * 0.5:
                print("\n❌ ВЫВОД: Скорее всего парсится ЛИЧНАЯ ЛЕНТА, а не группы!")
            elif len(common_ids) == 0:
                print("\n✓ ВЫВОД: Группы возвращают разные обсуждения - всё ОК!")
            else:
                print("\n⚠ ВЫВОД: Есть некоторое пересечение - нужна дополнительная проверка")
    
    return results


if __name__ == "__main__":
    # Тестируем две разные группы
    # Первая - группа, которую тестировали раньше
    group1 = "52932403593390"  # САМОДЕЛЬНЫЕ СТАНКИ И ИНСТРУМЕНТЫ
    
    # Вторая - любая другая известная группа
    # Используем тестовую группу или берем из аргументов командной строки
    if len(sys.argv) > 1:
        group2 = sys.argv[1]
    else:
        # Пример другой группы - можно заменить на реальную
        group2 = "56702726962489"  # Тестовая группа
    
    test_groups([group1, group2])

