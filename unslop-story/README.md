# Unslop story video

`trustloop-unslop.mp4`: a 9-second square video of the TrustLoop landing page redesigning itself, from the
original version to the current one (spacing, then colour and type, then copy, then details and the product
preview). Made with unslop by Damir Sokolovsky (@heydamir, CC BY 4.0); the credit is in the video.

- `story.html`: the story file. Step 0 is the original page; each step adds CSS on top.
- `fonts/`: IBM Plex, bundled so the video renders the same everywhere (SIL Open Font License).

Re-render (needs Playwright and ffmpeg):

    node .claude/skills/unslop/scripts/story.mjs unslop-story/story.html unslop-story/trustloop-unslop.mp4
