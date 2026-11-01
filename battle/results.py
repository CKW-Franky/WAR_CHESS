"""Battle end and game-over click handling for quick mode."""
from config import GAMEPLAY, AWAITING_DIRECTION, GAME_OVER, MAIN_MENU


class ResultsMixin:
    def check_game_over(self):
        if self.game_state not in (GAMEPLAY, AWAITING_DIRECTION):
            return

        player_alive = any(u.team == "player" and u.is_alive()
                           for u in self.units)
        ai_alive = any(u.team == "ai" and u.is_alive() for u in self.units)
        if player_alive and ai_alive:
            return

        self.game_state = GAME_OVER
        self.player_won = player_alive and not ai_alive

    def _handle_game_over_click(self, pos):
        if self.restart_btn.collidepoint(pos):
            self._start_quick_mode()
        elif self.exit_btn.collidepoint(pos):
            self.game_state = MAIN_MENU
