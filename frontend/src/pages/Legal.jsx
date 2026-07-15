import { Link, useParams } from "react-router-dom";

const content = {
  about: ["About AeroPulse", "AeroPulse helps individuals and teams turn live environmental measurements into clear AI AQI predictions, health guidance, forecasts, and shareable reports."],
  contact: ["Contact", "For support, product questions, or data concerns, email support@aeropulse.app."],
  faq: ["Frequently asked questions", "Choose a location or use current GPS. AeroPulse fetches weather and air-pollution data, runs the production model, and creates your prediction report automatically."],
  privacy: ["Privacy Policy", "We use your account information and saved prediction history to provide the service. We do not sell personal information."],
  terms: ["Terms of Service", "Use AeroPulse responsibly. Predictions are informational estimates and should not replace official public-health guidance."],
};

export default function Legal({ page: suppliedPage }) {
  const { page } = useParams();
  const [title, body] = content[suppliedPage || page] || content.about;
  return (
    <main className="min-h-screen max-w-3xl mx-auto p-8 md:p-16">
      <Link to="/" className="text-primary text-sm">← AeroPulse</Link>
      <h1 className="font-display text-4xl font-bold mt-8">{title}</h1>
      <p className="mt-6 leading-7 text-muted-foreground">{body}</p>
      <p className="mt-8 text-xs text-muted-foreground">Last updated: July 15, 2026</p>
    </main>
  );
}
