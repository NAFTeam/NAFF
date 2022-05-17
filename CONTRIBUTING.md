## Getting Started
Before contributing to the library, we strongly advise enabling the library's debugging features, and changing the logging level to `DEBUG`.
If you're unsure how to do that, copy the following snippet

```python
logging.basicConfig()
cls_log = logging.getLogger(naff.const.logger_name)
cls_log.setLevel(logging.DEBUG)

bot.load_extension("naff.ext.debug_extension")

bot = Client(..., asyncio_debug=True)
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

---

### Your commits

Your commits must comply with the following requirements, if they do not, where possible, a contributor will `squash` your commits, if that is not possible, you will be asked to rename them.

Your commits must comply with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary). For a short summary, your commits must have a prefix that outlines their intent. For example:

`feat: Adds support for modals`

Here is a quick reference for acceptable prefixes, and their meanings:

| Prefix | Name | Description |
| ----------- | ------------------------ | ---------------------------------------------------------------------------------- |
| feat        | Features                 | A new feature                                                                      |
| fix         | Bug Fixes                | A bug fix                                                                          |
| docs        | Documentation            | Documentation only changes                                                         |
| style       | Styles                   | Changes that do not affect the meaning of the code (white-space, formatting, etc.) |
| refactor    | Code Refactoring         | A code change that neither fixes a bug, nor adds a feature                         |
| perf        | Performance Improvements | A code change that improves performance                                            |
| test        | Tests                    | Adding tests or correcting existing tests                                          |
| build       | Builds                   | Changes that affect the build system, or external dependencies                     |
| ci          | Continuous-Integration   | Changes to our CI configuration files and scripts                                  |
| chore       | Chores                   | Other changes that do **not** modify source or test files                          |
| revert      | Reverts                  | Reverts a previous commit                                                          |

Should your commit introduce a breaking change, you should add either an `!` or `💥` just after the prefix.

ie.
`feat💥: User/Member permission methods are no longer async`

---

## Aftermath

Congrats on getting your pull request merged! If this PR pushed you over the threshold, you'll get a message offering you the `Contributor` role in our Discord server.
