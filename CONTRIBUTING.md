# Contributing to CampusBite

Thank you for considering a contribution. Bug reports, thoughtful feature
proposals, documentation improvements, and code changes are welcome.

## Before you start

- Check existing issues and pull requests to avoid duplicating work.
- For larger changes, open an issue first to discuss the proposed approach.
- For bugs, include steps to reproduce, what you expected, and what happened.
- For feature ideas, explain the use case and the benefit to customers, owners,
  riders, or maintainers.
- Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Set up the project

The project can be run with Docker Compose or locally. For local development,
follow the setup instructions in the [README](README.md#run-locally-without-docker).
Use Python 3.12 and Node.js 22, matching the CI configuration.

## Make and verify your changes

Keep changes focused and use the existing code style and patterns. Include or
update tests when behavior changes, and update documentation when setup or user
facing behavior changes.

Run the backend test suite from the repository root:

```powershell
python -m pytest -v
```

Run the frontend checks from the `frontend` directory:

```powershell
npm ci
npm run lint
npm run build
```

The pull request should pass the backend tests, frontend lint, and frontend
production build. Do not include secrets, local `.env` files, generated
dependencies, or local database files in a contribution.

## Open a pull request

1. Create a branch for your change.
2. Make a focused change and verify it with the relevant checks above.
3. Open a pull request against the repository's default branch.
4. Describe the problem and solution, link any related issue, list the checks
   you ran, and include screenshots for visible UI changes when helpful.
5. Respond to review feedback and update the pull request as needed.

By submitting a contribution, you confirm that you have the right to submit it
and that you are not including someone else's work without permission. Unless a
different license is stated for a specific contribution, contributions to this
repository are offered under the repository's [MIT License](LICENSE).
