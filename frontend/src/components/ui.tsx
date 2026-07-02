import type { ButtonHTMLAttributes, InputHTMLAttributes, LabelHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 ${className}`}>
      {children}
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  const base = 'w-full rounded-2xl px-5 py-4 text-base font-medium transition active:scale-[0.98] disabled:opacity-50'
  const styles = {
    primary: 'bg-brand-blue text-white hover:bg-brand-blue-dark',
    secondary: 'bg-brand-gray text-gray-800 hover:bg-gray-200',
    ghost: 'bg-transparent text-brand-blue hover:bg-brand-gray',
  }
  return <button className={`${base} ${styles[variant]} ${className}`} {...props} />
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-left">
      <span className="mb-1 block text-sm font-medium text-gray-600">{label}</span>
      {children}
    </label>
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20"
    />
  )
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20"
    />
  )
}

export function Label(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} />
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'gray' | 'green' | 'red' | 'amber' }) {
  const tones = {
    blue: 'bg-blue-50 text-brand-blue',
    gray: 'bg-gray-100 text-gray-600',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-600',
    amber: 'bg-amber-50 text-amber-600',
  }
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

export function IconButton({
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`flex h-9 w-9 items-center justify-center rounded-full bg-brand-gray text-gray-500 hover:bg-gray-200 ${className}`}
      {...props}
    />
  )
}
