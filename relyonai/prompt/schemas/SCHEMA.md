# schema

![schema](relyonai.excalidraw.png)

## system
```
{system overview}
- {system point 0}
- {system point 1} 
{etc.}
```

## user

### task

```
TASK: """
{task}
"""
ARGS: {comma list of args}
- {arg1}: """
{arg1 explanation, up to relyonai.TRUNCATE_REPR chars}
"""
- {arg2}: """
{arg2 explanation, up to relyonai.TRUNCATE_REPR chars}
"""
{etc.}
```

### result

```
RESULT: """
{repr(result), up to relyonai.TRUNCATE_REPR chars}
"""
```

### error

```
ERROR: """
{print error (last message), up to relyonai.TRUNCATE_REPR chars}
"""
```

## assistant

```
\```python
{code}
[final_]result = {result expression}
# or 
raise RelyOnAIError({error message})
\```
```
