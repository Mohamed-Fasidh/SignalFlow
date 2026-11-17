"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="error-screen"><section className="error-card"><span className="error-mark">!</span><h1>Something went wrong</h1><p>SignalFlow AI could not complete this request. You can try loading this screen again.</p><button className="primary-button" onClick={() => reset()}>Try again</button></section></main>;
}
