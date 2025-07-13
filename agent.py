import os
import importlib.util

def run_task_by_name(task_name):
    """
    Dynamically imports and runs a task by its name.
    """
    tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks')
    module_path = os.path.join(tasks_dir, f"{task_name}.py")

    if not os.path.exists(module_path):
        print(f"[!] Task '{task_name}' not found at '{module_path}'")
        return

    try:
        spec = importlib.util.spec_from_file_location(task_name, module_path)
        task_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_module)
        
        if hasattr(task_module, 'run_task'):
            print(f"-> Running task: '{task_name}'")
            task_module.run_task()
        else:
            print(f"- Task '{task_name}' does not have a 'run_task' function.")

    except Exception as e:
        print(f"[!] Error running task '{task_name}': {e}")

def main():
    """
    The main function of the agent.
    It runs the data acquisition and processing tasks in a specific order.
    """
    print("--- Starting data processing agent ---")

    # 1. Download the latest seismic data
    run_task_by_name('download_sismos_html')

    # 2. Parse the downloaded file and update the database
    run_task_by_name('parse_sismos_file')

    print("--- Agent has finished all tasks. ---")

if __name__ == "__main__":
    main()
