# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

- `frontend/` - Vue 3 application with TypeScript
- `LICENSE` - MIT License (Copyright 2025 Paul Panțiru)

## Frontend Development (Vue 3)

Located in `frontend/` directory. Built with:
- Vue 3 with TypeScript
- Vue Router for routing
- Pinia for state management
- Vitest for testing
- ESLint for linting
- Prettier for code formatting

### Common Commands

```bash
cd frontend
npm run dev        # Start development server
npm run build      # Build for production
npm run preview    # Preview production build
npm run test:unit  # Run unit tests
npm run lint       # Run ESLint
npm run format     # Format code with Prettier
```

### Development Workflow

1. Navigate to `frontend/` directory for all frontend work
2. Use `npm run dev` to start the development server
3. Run `npm run lint` and `npm run format` before committing changes
4. Use `npm run test:unit` to run tests