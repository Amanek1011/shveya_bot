# states.py
from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_job = State()
    waiting_for_machine_number = State()

# Состояния для управления пользователями
class UserManagementStates(StatesGroup):
    waiting_for_action = State()  # Выбор действия
    waiting_for_user_selection = State()  # Выбор пользователя
    waiting_for_confirmation = State()  # Подтверждение удаления

class ZakroiStates(StatesGroup):
    waiting_for_party_number = State()
    waiting_for_color = State()
    waiting_for_quantity_line = State()

class MaterialManagementStates(StatesGroup):
    waiting_for_confirmation = State()

# Состояния для управления партиями
class PartyManagementStates(StatesGroup):
    waiting_for_action = State()  # Выбор действия
    waiting_for_party_selection = State()  # Выбор партии для удаления
    waiting_for_confirmation = State()  # Подтверждение удаления

class FourXStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_machine_number = State()
    waiting_for_count = State()

# ДОБАВЛЯЕМ НЕДОСТАЮЩИЕ СОСТОЯНИЯ:

class RaspashStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class BeikaStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class StrochkaStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class GorloStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class YtygStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class OtkStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class UpakovkaStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_count = State()

class EditOperationsStates(StatesGroup):
    waiting_for_party_selection = State()
    waiting_for_color_selection = State()
    waiting_for_operation = State()
    waiting_for_new_count = State()