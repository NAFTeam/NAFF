name: Feature request
description: I would like something added
title: "[FEAT] Your title here"
labels: enhancement
assignees: ''
body:
  - type: markdown
    attributes:
      value: >
        Please fill all the required fields.
  - type: input
    attributes:
      label: Is your feature request related to a problem? Please describe.
      description: A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]
    validations:
      required: true
  - type: textarea
    attributes:
      label: Describe the solution you'd like
      description: >
         A clear and concise description of what you want to happen.
    validations:
      required: true
  - type: textarea
    attributes:
      label: Describe alternatives you've considered
      description: >
        A clear and concise description of any alternative solutions or features you've considered.
  - type: textarea
    attributes:
      label: Additional information
      description: >
        A clear and concise description of what you expected to happen.
