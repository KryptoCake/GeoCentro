import os
import importlib.util
import time

def main():
    """
    The main function of the agent.
    It discovers and runs tasks from the 'tasks' directory.
    """
    tasks_dir = os.path.join(os.path.dirname(__file__), 'tasks')
    print(f"Searching for tasks in: {tasks_dir}")

    if not os.path.isdir(tasks_dir):
        print(f"Error: Tasks directory not found at '{tasks_dir}'")
        return

    while True:
        print("\n--- Agent is running. Checking for tasks... ---")
        for filename in os.listdir(tasks_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                task_name = filename[:-3]
                try:
                    module_path = os.path.join(tasks_dir, filename)
                    
                    # Dynamically import the task module
                    spec = importlib.util.spec_from_file_location(task_name, module_path)
                    task_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(task_module)
                    
                    # Look for a 'run_task' function and execute it
                    if hasattr(task_module, 'run_task'):
                        print(f"-> Running task: '{task_name}'")
                        task_module.run_task()
                    else:
                        print(f"- Task '{task_name}' does not have a 'run_task' function.")
                        
                except Exception as e:
                    print(f"[!] Error running task '{task_name}': {e}")
        
        print("--- Finished checking tasks. Waiting for next cycle... ---")
        # Wait for 5 minutes before the next cycle
        time.sleep(300)

if __name__ == "__main__":
    main()
