from __future__ import annotations
import re
from .default import ActionState, BaseActionSpace
# from default import ActionState, BaseActionSpace

class CUAActionSpace(BaseActionSpace):
    def __init__(
        self
    ) -> None:
        super().__init__(CUAActionSpace)
        self.ACTION_PREFIX = "<|action_start|>"
        self.ACTION_SUFFIX = "<|action_end|>"
        self.THINK_PREFIX = "<think>"
        self.THINK_SUFFIX = "</think>"

    def load_action(
        self,
        response_content: str | dict
    ) -> ActionState:
        import re
        PATTERN = re.compile(r'^(\w+)\s*\((.*)\)\s*$')

        if isinstance(response_content, str):
            think_content = ""
            action_content = response_content.strip()

            think_re = re.compile(rf"{self.THINK_PREFIX}(.*?){self.THINK_SUFFIX}", re.DOTALL)
            action_re = re.compile(rf"(?:{re.escape(self.ACTION_PREFIX)})?(.*?){re.escape(self.ACTION_SUFFIX)}", re.DOTALL)

            if think_m := think_re.search(response_content):
                think_content = think_m.group(1).strip()

            if action_m := action_re.search(response_content):
                action_content = action_m.group(1).strip()
                print(action_content)

        action_list = action_content.replace("and", "|").replace("｜", "|").split("|")
        action = self.load_default_action()
        action.think = think_content
        for action_item in action_list:
            action_item = action_item.strip()
            if matches := PATTERN.match(action_item):
                cua_function, cua_args = matches.group(1),matches.group(2)
                cua_args.replace("/'", "")
                if cua_function == "keyPress":
                    key = cua_args
                    if key == "esc":
                        action.ESC = 1
                    elif key == "s":
                        action.back = 1
                    elif key == "w":
                        action.forward = 1
                    elif key == "a":
                        action.left = 1
                    elif key == "d":
                        action.right = 1
                    elif key == "q":
                        action.drop = 1
                    elif key == "space":
                        action.jump = 1
                    elif key == "left.shift":
                        action.sneak = 1
                    elif key == "left.ctrl":
                        action.sprint = 1
                    elif key == "e":
                        action.inventory = 1
                    elif key in "123456789":
                        action.hotbars[int(key) - 1] = 1
                elif cua_function == "mouseClick":
                    click_button = cua_args.replace("\"", "").replace("\'", "")
                    if click_button == "left":
                        action.attack = 1
                    elif click_button == "right":
                        action.use = 1
                elif cua_function == "mouseMove":
                    pitch, yaw = tuple(map(float, cua_args.split(",")))
                    action.camera = [pitch, yaw]
        
        if not self.validate_action(action):
            action = self.load_default_action()
            
        return action
                
                
                
if __name__ == "__main__":
    cua = CUAActionSpace()
    resp = "keyPress(w)｜keyPress(space)｜keyPress(left.ctrl)<|action_end|>"
    a = cua.load_action(resp)