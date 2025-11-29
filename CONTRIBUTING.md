# Contributing to `tidal-dl-ng`

Contributions are welcome, and they are greatly appreciated!
Every little bit helps, and credit will always be given.

You can contribute in many ways:

# Types of Contributions

## Report Bugs

Report bugs at https://github.com/exislow/tidal-dl-ng/issues

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs.
Anything tagged with "bug" and "help wanted" is open to whoever wants to implement a fix for it.

## Implement Features

Look through the GitHub issues for features.
Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

## Write Documentation

Cookiecutter PyPackage could always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at https://github.com/exislow/tidal-dl-ng/issues.

If you are proposing a new feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

# Get Started!

Ready to contribute? Here's how to set up `tidal-dl-ng` for local development.
Please note this documentation assumes you already have `poetry` and `Git` installed and ready to go.

1. Fork the `tidal-dl-ng` repo on GitHub.

2. Clone your fork locally:

```bash
cd <directory_in_which_repo_should_be_created>
git clone git@github.com:YOUR_NAME/tidal-dl-ng.git
```

3. Now we need to install the environment. Navigate into the directory

```bash
cd tidal-dl-ng
```

If you are using `pyenv`, select a version to use locally. (See installed versions with `pyenv versions`)

```bash
pyenv local <x.y.z>
```

Then, install and activate the environment with:

```bash
poetry install
poetry shell
```

4. Install pre-commit to run linters/formatters at commit time:

```bash
poetry run pre-commit install
```

5. Create a branch for local development:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

6. Don't forget to add test cases for your added functionality to the `tests` directory.

7. When you're done making changes, check that your changes pass the formatting tests.

   **On Linux/macOS:**

   ```bash
   make check
   ```

   **On Windows PowerShell (equivalent commands):**

   ```powershell
   poetry check --lock
   poetry run pre-commit run -a
   poetry run deptry .
   ```

8. Now, validate that all unit tests are passing:

   **On Linux/macOS:**

   ```bash
   make test
   ```

   **On Windows PowerShell (equivalent):**

   ```powershell
   poetry run pytest --doctest-modules
   ```

9. Before raising a pull request you should also run tox.
   This will run the tests across different versions of Python:

   ```bash
   tox
   ```

   **Note:** This requires you to have multiple versions of Python installed.
   This step is also triggered in the CI/CD pipeline, so you could also choose to skip this step locally.

   **Windows users:** If `tox` fails with Git/dulwich errors (like `KeyError: b'HEAD'`), you can skip this step as the CI/CD pipeline will run it automatically when you create a pull request. Make sure you have committed your changes to Git before running tox:

   ```powershell
   git add .
   git commit -m "Your changes"
   # Then try tox again, or skip it and rely on CI/CD
   ```

10. Commit your changes and push your branch to GitHub:

```bash
git add .
git commit -m "Your detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

11. Submit a pull request through the GitHub website.

# Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.

2. If the pull request adds functionality, the docs should be updated.
   Put your new functionality into a function with a docstring, and add the feature to the list in `README.md`.

# Troubleshooting

## Windows-specific Issues

### Tox fails with UnicodeDecodeError or KeyError: b'HEAD'

This is a known issue on Windows when:

- The Git repository doesn't have a valid HEAD (no commits yet)
- There are encoding issues with Git output

**Solutions:**

1. Make sure you have at least one commit in your Git repository:

   ```powershell
   git status  # Check if you have uncommitted changes
   git add .
   git commit -m "Initial commit"
   ```

2. If the error persists, you can skip `tox` locally and rely on the CI/CD pipeline to run it when you create a pull request.

3. Alternatively, run the tests manually for your Python version:
   ```powershell
   poetry run pytest --doctest-modules
   ```

### Make commands don't work on Windows

If you're on Windows and `make` is not available, use the PowerShell equivalent commands documented in steps 7 and 8 above, or install `make` for Windows (e.g., via Chocolatey: `choco install make`).
