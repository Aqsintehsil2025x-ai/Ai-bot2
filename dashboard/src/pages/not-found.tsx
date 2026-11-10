import { ArrowLeft, Flower2 } from 'lucide-react';
import { Link } from 'wouter';

export default function NotFound() {
  return (
    <main className="not-found">
      <section className="not-found-card">
        <Flower2 size={36} strokeWidth={1.4}/>
        <h1>Burada değil.</h1>
        <p>Aradığın sayfayı bulamadık. Ana sayfadan devam edebilirsin.</p>
        <Link href="/" className="button-primary focus-ring" data-testid="link-not-found-home"><ArrowLeft size={15}/>Ana sayfaya dön</Link>
      </section>
    </main>
  );
}
