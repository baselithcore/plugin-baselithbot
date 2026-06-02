import { motion } from 'framer-motion';
import { Cross } from 'lucide-react';

interface WelcomeProps {
  onBegin: () => void;
  pending: boolean;
}

export function Welcome({ onBegin, pending }: WelcomeProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="m-auto flex max-w-lg flex-col items-center gap-5 px-4 py-10 text-center"
    >
      <Cross
        className="h-16 w-16 text-gold-bright opacity-90 drop-shadow-[0_0_20px_rgba(201,168,106,0.4)]"
        strokeWidth={1.2}
      />
      <h1 className="font-serif text-3xl font-normal italic tracking-wide text-parchment sm:text-4xl">
        Sia lodato Gesù Cristo
      </h1>
      <p className="max-w-md font-serif text-base italic leading-relaxed text-parchment-soft sm:text-lg">
        «Padre, ho peccato contro il Cielo e contro di te;
        <br />
        non sono più degno di essere chiamato tuo figlio.»
      </p>
      <p className="mt-2 text-[0.72rem] uppercase tracking-[0.16em] text-ash">
        Quando sei pronto, accosta il cuore al confessionale
      </p>
      <button
        type="button"
        disabled={pending}
        onClick={onBegin}
        className="mt-3 rounded-full bg-gradient-to-b from-gold-bright to-gold px-8 py-3 text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-void shadow-glow-gold transition-all duration-300 hover:-translate-y-0.5 hover:shadow-glow-gold-strong active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {pending ? 'Apertura…' : 'Accosta · Inizia il rito'}
      </button>
    </motion.div>
  );
}
