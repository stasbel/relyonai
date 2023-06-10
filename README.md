# relyonai

![](showcase.png)

runtime inline python ai calls

## usage

```
pip install relyonai
```

```python
from relyonai import ai
f = ai('get print hello world func')
f()
```

```python
from relyonai import config
config.model = 'gpt-4'
```

## reflections & 0.2 plans

overall, the thing works to some extent, though it lacks **reliability** and **controlability**
the main problem is gpt-3.5 don't listen to system message and keen to generate **nonsense**
major improvements could be made when gpt-4 becomes 10x cheaper and 2x faster

- [ ] improve quality
  - [ ] better, more sophisticated tests, self-testing
  - [ ] include invocation context (`ai`, ±5 above/below exprs)
  - [ ] better system prompt with gpt-4 (it's working)
  - [ ] include project info / files / pip / hardware / os / time / etc.
  - [ ] implement final result check
  - [ ] examples.json for different py versions
  - [ ] other runtimes: bash, remote, c++, etc.
- [ ] better introspection
  - [ ] `rich` dialogue printint (+spinner)
  - [ ] much better error handling
  - [ ] view source code/doc
  - [ ] more granular sessions (trees)
- [ ] advanced caching
  - [ ] redis
  - [ ] limit size (up to ~20mb)
  - [ ] save pre-compiled code
- [ ] async
  - [ ] aai
  - [ ] agpt
  - [ ] aemb

## License

[MIT](LICENSE)
