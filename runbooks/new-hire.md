---
title: New hire setup
audience: it
tags: [joiner, onboarding, new-hire, hris]
summary: How a joiner from the HR feed becomes an account.
---

# New hire setup

1. The person must already be a row in the synthetic HR file with status hired.
2. The assistant calls run_joiner with the email, department, and title from that row.
3. IT approves. Only then does the lab create the directory user, the Google Workspace mock user, and the department groups.
4. phi-access is never added by a joiner. A laptop stays pending enrollment until the mock inventory is updated.
