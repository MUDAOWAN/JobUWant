This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## 2026-08-02 Live Workflow Wiring

The frontend API client and pages now support live task workflow controls:

- `POST /api/tasks`
- `POST /api/tasks/{task_id}/actions/start-collection`
- `POST /api/tasks/{task_id}/actions/start-scoring`
- `POST /api/tasks/{task_id}/sample`
- `POST /api/tasks/{task_id}/actions/start-structuring`
- `POST /api/tasks/{task_id}/actions/run-structuring-batches`
- `POST /api/tasks/{task_id}/actions/build-report-input`
- `POST /api/tasks/{task_id}/actions/write-final-report`

Verification passed with lint, typecheck, and production build.
## 2026-08-05 Create Task Form Update

The `/tasks` page now loads `GET /api/cities` and renders a grouped city selector. City code, source type, and batch size are hidden from the user-facing form. Target count is validated inline and cannot exceed 200.
