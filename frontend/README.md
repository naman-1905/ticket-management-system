# Frontend

Next.js frontend for the Ticket Management System.

## Setup

```bash
npm install
cp .env.example .env.local
```

Set the backend API URL in `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Development

```bash
npm run dev
```

Open `http://localhost:3000`.

## Scripts

| Command | Description |
| ------- | ----------- |
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |

## Structure

```text
app/
├── components/     # Shared UI components
├── dashboard/      # Staff dashboard
├── tickets/        # Ticket list, detail, and creation
├── sla/            # SLA management
├── customers/      # Organization management
├── admin/          # Users and audit logs
├── portal/         # Customer-facing pages
├── login/          # Authentication
└── register/
lib/
├── api.js          # API client
├── auth-context.js # Auth state
└── permissions.js  # Role and permission helpers
```

See the [root README](../README.md) for full project setup.
