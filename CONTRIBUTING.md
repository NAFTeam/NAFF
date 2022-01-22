## Getting Started
Before contributing to the library, we strongly advise enabling the library's debugging features, and changing the logging level to `DEBUG`.
If you're unsure how to do that, copy the following snippet
```python
logging.basicConfig()
cls_log = logging.getLogger(dis_snek.const.logger_name)
cls_log.setLevel(logging.DEBUG)

bot.grow_scale("dis_snek.ext.debug_scale")

bot = Snake(..., asyncio_debug=True)
```
---

## Requirements

For a pull-request to be merged, your pull request must fullfill the following:
-  [x] Your code must be black formatted
-  [x] Your pull request must target the `dev` branch
-  [x] You must have *actually* tested your code
-  [x] You must fully document the changes of which you are making

Assuming your code is compliant with the above, the pull request will need to be reviewed by **2** contributors.
The contributors will review your code and highlight any changes they suggest be made.

## Aftermath

Congrats on getting your pull request merged! If this PR pushed you over the threshold, you'll get a message offering you the `Contributor` role in our Discord server.
