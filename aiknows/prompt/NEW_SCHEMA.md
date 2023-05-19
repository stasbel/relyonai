# schema

* everything is truncated to `aiknows.config.n_truncate_repr` chars

## system

* system overview is giving in markdown
* refined with gpt-4 multiple times
* describe this schema in details

## user

### task

```
TASK: """
{task}
"""
ENV: [new|same]
ARGS:
- {arg1}: """
type: {type1}
{...}
"""
- {arg2}: """
type: {type2}
{...}
"""
{etc.}
```

### result

```
RESULT: """
{repr(last expression)}
"""
```

### error

```
ERROR: """
{print error (last message)}
"""
```

## assistant

```
\```python
{code}
\```
```
