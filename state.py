# project_v1/state.py
from collections import defaultdict

class StateManager:
    def __init__(self):
        self.state = defaultdict(dict)

    def get_state(self, user_id):
        return self.state[user_id]

    def set_state(self, user_id, new_state):
        self.state[user_id] = new_state

state_manager = StateManager()
