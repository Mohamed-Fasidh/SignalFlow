import Link from "next/link";

export default function NotFound() {
  return <main className="error-screen"><section className="error-card"><span className="error-mark">404</span><h1>Page not found</h1><p>The page you’re looking for isn’t available in this workspace.</p><Link className="primary-button link-button" href="/">Back to overview</Link></section></main>;
}
