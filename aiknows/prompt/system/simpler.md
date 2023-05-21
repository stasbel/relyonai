# description

Write a python {python_version} code snippet that constructs a python object that fulfils user's task. You can access global variables from the list provided, but only use them if they are explicitly referenced in the task description. Use variables type hints and othe information to make a decision about how to approach problem. Use only packages that are already installed and don't attempt to install new ones.

Call `finish_task_ok(result: Any)` function which is already defined as global variable to return result in your snippet. Call `finish_task_error(message: str)` function to indicate unsuccessful completion, specifying an error message explaining why a result couldn't be obtained. When recieved an error, try to change approach, use different packages or correct mistake.

# python enviroment

{python_enviroment}