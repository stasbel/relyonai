# relyonai

## usage

```python
from relyonai import ai
```

## `-> 0.2` future plans

- [ ] improve quality
  - [ ] better, more sophisticated tests, self-testing
  - [ ] include invocation context (`ai`, ±5 above/below exprs)
  - [ ] better system prompt with gpt-4 (it's working)
  - [ ] include project info / files / pip / hardware / os / time / etc.
  - [ ] implement final result check
  - [ ] examples.json for different py versions
  - [ ] other runtimes: bash, remote, c++, etc.
- [ ] async
  - [ ] agpt
  - [ ] aemb
  - [ ] aai
- [ ] advanced caching
  - [ ] redis
  - [ ] limit size (up to ~20mb)
  - [ ] save pre-compiled code?
- [ ] better introspection
  - [ ] `rich` dialogue printint (+spinner)
  - [ ] much better error handling
  - [ ] view source code/doc
  - [ ] more granular sessions (trees)
