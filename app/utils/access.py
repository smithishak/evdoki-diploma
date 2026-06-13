"""Проверка прав: техник/админ определяется по белому списку из конфига."""

from __future__ import annotations


def is_admin(vk_id: int, admin_ids: list[int]) -> bool:
    """True, если VK ID есть в списке техников/админов."""
    return vk_id in admin_ids
