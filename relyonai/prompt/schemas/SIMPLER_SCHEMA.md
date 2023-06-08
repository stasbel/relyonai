# simpler schema

## plan

1. ✅ focus on single-response/no-lambdas tasks
    - ✅ better code parsing with regexp
    - ✅ better tests and incremential support
        - ✅ imports
        - ✅ consts
        - ✅ files
        - ✅ ...
2. ✅ +lambdas tasks
    - ...
3. ✅ `gpt` function
    - ...
4. reusable namespaces
    - ...
5. move to multi-response tasks
    - ...

## schema

```
{simple system}

task description: """
{...}
"""
global variables:
- {var1} ({type1})
    - {var1}: description
```
