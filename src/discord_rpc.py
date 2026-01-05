import logging
import threading
import time
from typing import Any

try:
    from pypresence import Presence
    PYPRESENCE_AVAILABLE = True
except ImportError:
    PYPRESENCE_AVAILABLE = False
    logging.warning('pypresence не установлен. Discord Rich Presence будет отключен.')


DISCORD_APP_ID = '1432409873500344451'


class DiscordRPC:
    
    def __init__(self) -> None:
        self.rpc: Presence | None = None
        self.is_connected: bool = False
        self.loop_thread: threading.Thread | None = None
        self.running: bool = False
        self.start_time: int = 0
        
        if not PYPRESENCE_AVAILABLE:
            logging.warning('Discord Rich Presence отключен (pypresence не установлен)')
            return
        
        try:
            self.rpc = Presence(DISCORD_APP_ID)
            logging.info('Discord Rich Presence инициализирован')
        except Exception as e:
            logging.exception(f'Ошибка инициализации Discord RPC: {e}')
            self.rpc = None
    
    def connect(self) -> bool:
        if not self.rpc:
            return False
        
        try:
            self.rpc.connect()
            self.is_connected = True
            self.start_time = int(time.time())
            logging.info('✅ Подключено к Discord Rich Presence')
            
            self.running = True
            self.loop_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.loop_thread.start()
            
            return True
        except Exception as e:
            logging.exception(f'Ошибка подключения к Discord: {e}')
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        self.running = False
        if self.loop_thread:
            self.loop_thread.join(timeout=2)
        if self.rpc and self.is_connected:
            try:
                self.rpc.close()
            except Exception as e:
                logging.exception(f'Ошибка при отключении от Discord: {e}')
            self.is_connected = False
            logging.info('Отключено от Discord Rich Presence')
    
    def update_status(
        self,
        state: str = 'В лаунчере',
        details: str = '',
        large_image: str | None = None,
        large_text: str = '16Launcher',
        small_image: str | None = None,
        small_text: str = '',
        buttons: list[dict[str, str]] | None = None,
    ) -> None:
        if not self.rpc or not self.is_connected:
            return
        
        try:
            presence_data: dict[str, Any] = {
                'state': state,
                'large_image': large_image or 'launcher_icon',
                'large_text': large_text,
                'start': self.start_time,
            }
            
            if details:
                presence_data['details'] = details
            if small_image:
                presence_data['small_image'] = small_image
            if small_text:
                presence_data['small_text'] = small_text
            if buttons:
                presence_data['buttons'] = buttons
            
            self.rpc.update(**presence_data)
            logging.debug(f'Статус Discord обновлён: {state}')
        except Exception as e:
            logging.exception(f'Ошибка обновления статуса Discord: {e}')
    
    def set_menu_status(self) -> None:
        self.update_status(
            state='Просматривает лаунчер',
            details='В главном меню',
        )
    
    def set_playing_status(self, version: str, loader: str | None = None) -> None:
        loader_names = {
            'vanilla': 'Vanilla',
            'forge': 'Forge',
            'fabric': 'Fabric',
            'optifine': 'OptiFine',
            'quilt': 'Quilt',
        }
        
        loader_name = loader_names.get(loader, 'Minecraft') if loader else ''
        details = f'{loader_name} {version}' if loader_name else version
        
        self.start_time = int(time.time())
        
        self.update_status(
            state='Играет в Minecraft',
            details=details,
            large_image='minecraft',
            large_text=f'Minecraft {version}',
            small_image='launcher_icon',
            small_text='16Launcher',
        )
    
    def set_downloading_status(self, progress: str) -> None:
        self.update_status(
            state='Загружает файлы',
            details=progress,
        )
    
    def set_launching_status(self) -> None:
        self.update_status(
            state='Запускает игру',
            details='Подготовка к запуску...',
        )
    
    def _update_loop(self) -> None:
        """Цикл обновления статуса Discord"""
        while self.running:
            if self.is_connected:
                try:
                    time.sleep(15)
                except Exception as e:
                    logging.exception(f'Ошибка в цикле обновления Discord: {e}')
            else:
                break


_discord_rpc: DiscordRPC | None = None


def get_discord_rpc() -> DiscordRPC:
    global _discord_rpc
    if _discord_rpc is None:
        _discord_rpc = DiscordRPC()
    return _discord_rpc


def init_discord_rpc() -> bool:
    try:
        rpc = get_discord_rpc()
        return rpc.connect()
    except Exception as e:
        logging.exception(f'Ошибка инициализации Discord RPC: {e}')
        return False


def shutdown_discord_rpc() -> None:
    """Отключить Discord RPC"""
    global _discord_rpc
    if _discord_rpc:
        _discord_rpc.disconnect()
        _discord_rpc = None

