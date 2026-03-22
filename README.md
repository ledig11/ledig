# Windows Step Guide

A Windows-first step-by-step computer operation guidance assistant MVP.

## Goal
Help users complete computer operations step by step, one step at a time.

## MVP Scope
- Windows desktop only
- Screenshot-based guidance
- Floating step panel
- Screen highlight overlay
- Human-in-the-loop assistance

## Current Status
- FastAPI backend with `analyze` and `feedback` APIs
- WPF floating panel plus lightweight highlight overlay
- SQLite logging for analyze, feedback, sessions, and observation traces
- Backend session state tracking for current step and feedback counters
- Semi-real observation fields for foreground window title and primary screen size
- Local observation reference, local screenshot file attempt, and local manifest JSON
- Minimal foreground-window UIA summary captured on the client
- Candidate foreground-window UIA elements captured with bounding rectangles
- Model planner entry on the backend with safe fallback to mock planning

## Next
- Add richer prompt shaping and response validation for model-backed planning
- Strengthen replay / trace inspection around local screenshot and manifest assets
- Validate one real Windows task scenario end to end
