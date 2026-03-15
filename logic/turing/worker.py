from logic.turing.logic import WorkerState, TuringTask
from logic.turing.display.manager import MultiLineManager

class TuringWorker:
    def __init__(self, worker_id: str, manager: MultiLineManager):
        self.worker_id = worker_id
        self.manager = manager

    def execute(self, task: TuringTask, **kwargs):
        for step_func in task.steps:
            try:
                result_gen = step_func(**kwargs)
            except Exception as e:
                self.manager.update(self.worker_id, f"Step launch failed: {e}", is_final=True)
                return WorkerState.ERROR
            
            is_gen = hasattr(result_gen, '__next__') and hasattr(result_gen, '__iter__')
            if is_gen:
                try:
                    for update in result_gen:
                        self.manager.update(self.worker_id, update.display_text, is_final=update.is_final)
                        if update.state in [WorkerState.EXIT, WorkerState.ERROR]:
                            return update.state
                except Exception as e:
                    self.manager.update(self.worker_id, f"Step execution failed: {e}", is_final=True)
                    return WorkerState.ERROR
            else:
                if result_gen is None: continue
                self.manager.update(self.worker_id, result_gen.display_text, is_final=result_gen.is_final)
                if result_gen.state in [WorkerState.EXIT, WorkerState.ERROR]:
                    return result_gen.state
                    
        return WorkerState.SUCCESS
