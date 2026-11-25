
import { useState } from 'react'
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  Search,
  Lock,
  Unlock,
  Eye,
  X,
} from 'lucide-react'

type TransactionStatus = 'Verified' | 'On Hold' | 'Pending'

interface Transaction {
  id: string
  customer: string
  type: string
  amount: number
  beneficiary: string
  time: string
  status: TransactionStatus
  reason: string
}

const initialTransactions: Transaction[] = [
  {
    id: 'TXN-2026-001',
    customer: 'Rahul Sharma',
    type: 'Bank Transfer',
    amount: 25000,
    beneficiary: 'Amit Kumar',
    time: '10:42 AM',
    status: 'Verified',
    reason: 'Sample transaction. Independent verification recorded.',
  },
  {
    id: 'TXN-2026-002',
    customer: 'Priya Nair',
    type: 'UPI Transfer',
    amount: 85000,
    beneficiary: 'Unknown Beneficiary',
    time: '10:38 AM',
    status: 'On Hold',
    reason: 'Sample risk scenario: unusual amount and unverified beneficiary.',
  },
  {
    id: 'TXN-2026-003',
    customer: 'Arjun Rao',
    type: 'Bank Transfer',
    amount: 12000,
    beneficiary: 'Neha Rao',
    time: '10:25 AM',
    status: 'Pending',
    reason: 'Awaiting independent customer verification.',
  },
  {
    id: 'TXN-2026-004',
    customer: 'Sneha Iyer',
    type: 'UPI Transfer',
    amount: 5000,
    beneficiary: 'Kiran Stores',
    time: '10:12 AM',
    status: 'Verified',
    reason: 'Sample transaction. Independent verification recorded.',
  },
]

function Transactions() {
  const [transactions, setTransactions] = useState(initialTransactions)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Transaction | null>(null)

  const updateStatus = (id: string, status: TransactionStatus) => {
    setTransactions((previous) =>
      previous.map((transaction) =>
        transaction.id === id ? { ...transaction, status } : transaction
      )
    )

    setSelected((previous) =>
      previous?.id === id ? { ...previous, status } : previous
    )
  }

  const filteredTransactions = transactions.filter((transaction) =>
    [
      transaction.id,
      transaction.customer,
      transaction.beneficiary,
      transaction.type,
    ]
      .join(' ')
      .toLowerCase()
      .includes(search.toLowerCase())
  )

  const heldCount = transactions.filter((t) => t.status === 'On Hold').length
  const pendingCount = transactions.filter((t) => t.status === 'Pending').length
  const verifiedCount = transactions.filter((t) => t.status === 'Verified').length

  const statusStyle = (status: TransactionStatus) => {
    if (status === 'Verified') {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    }
    if (status === 'On Hold') {
      return 'bg-red-500/10 text-red-400 border-red-500/20'
    }
    return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium">
          <ShieldCheck size={17} />
          TRANSACTION SECURITY
        </div>
        <h1 className="text-2xl font-bold text-white mt-2">
          Transaction Guard
        </h1>
        <p className="text-slate-400 mt-1">
          Monitor transactions and manage security holds.
        </p>
      </div>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <div className="flex gap-3">
          <ShieldAlert className="text-amber-400 shrink-0" size={20} />
          <div>
            <p className="text-amber-300 text-sm font-semibold">
              Frontend demonstration mode
            </p>
            <p className="text-slate-400 text-sm mt-1">
              These are fictional transactions. Status changes are local UI
              demonstrations only. No real bank account or payment is affected.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-slate-400 text-sm">Total Transactions</p>
          <p className="text-3xl font-bold text-white mt-2">
            {transactions.length}
          </p>
          <p className="text-xs text-slate-500 mt-2">Sample records</p>
        </div>

        <div className="rounded-xl border border-emerald-500/20 bg-slate-900 p-5">
          <div className="flex justify-between">
            <p className="text-slate-400 text-sm">Verified</p>
            <ShieldCheck size={19} className="text-emerald-400" />
          </div>
          <p className="text-3xl font-bold text-emerald-400 mt-2">
            {verifiedCount}
          </p>
          <p className="text-xs text-slate-500 mt-2">Sample status</p>
        </div>

        <div className="rounded-xl border border-red-500/20 bg-slate-900 p-5">
          <div className="flex justify-between">
            <p className="text-slate-400 text-sm">On Hold</p>
            <Lock size={19} className="text-red-400" />
          </div>
          <p className="text-3xl font-bold text-red-400 mt-2">{heldCount}</p>
          <p className="text-xs text-slate-500 mt-2">Sample status</p>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-slate-900 p-5">
          <div className="flex justify-between">
            <p className="text-slate-400 text-sm">Pending</p>
            <Clock size={19} className="text-amber-400" />
          </div>
          <p className="text-3xl font-bold text-amber-400 mt-2">
            {pendingCount}
          </p>
          <p className="text-xs text-slate-500 mt-2">Sample status</p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
          <div>
            <h2 className="text-white font-semibold">Transaction Records</h2>
            <p className="text-slate-500 text-xs mt-1">
              Search and inspect sample transaction records
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search
              size={17}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search transactions..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2.5 pl-10 pr-3 text-sm text-white outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left min-w-[750px]">
            <thead>
              <tr className="border-b border-slate-800 text-xs text-slate-500">
                <th className="py-3 pr-4 font-medium">Transaction ID</th>
                <th className="py-3 pr-4 font-medium">Customer</th>
                <th className="py-3 pr-4 font-medium">Amount</th>
                <th className="py-3 pr-4 font-medium">Beneficiary</th>
                <th className="py-3 pr-4 font-medium">Status</th>
                <th className="py-3 font-medium">Action</th>
              </tr>
            </thead>

            <tbody>
              {filteredTransactions.map((transaction) => (
                <tr
                  key={transaction.id}
                  className="border-b border-slate-800/70 text-sm"
                >
                  <td className="py-4 pr-4 text-cyan-400 font-medium">
                    {transaction.id}
                  </td>
                  <td className="py-4 pr-4 text-slate-200">
                    {transaction.customer}
                    <p className="text-xs text-slate-500 mt-1">
                      {transaction.type}
                    </p>
                  </td>
                  <td className="py-4 pr-4 text-white font-semibold">
                    ₹{transaction.amount.toLocaleString('en-IN')}
                  </td>
                  <td className="py-4 pr-4 text-slate-300">
                    {transaction.beneficiary}
                  </td>
                  <td className="py-4 pr-4">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-xs ${statusStyle(transaction.status)}`}
                    >
                      {transaction.status}
                    </span>
                  </td>
                  <td className="py-4">
                    <button
                      onClick={() => setSelected(transaction)}
                      className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                    >
                      <Eye size={15} />
                      View
                    </button>
                  </td>
                </tr>
              ))}

              {filteredTransactions.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="py-10 text-center text-slate-500 text-sm"
                  >
                    No matching transactions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex items-center gap-2 mb-3">
          <Lock size={19} className="text-cyan-400" />
          <h2 className="text-white font-semibold">Transaction Authorization Policy</h2>
        </div>
        <p className="text-slate-400 text-sm leading-6">
          A voice call must never authorize a sensitive financial transaction
          by itself. Sensitive actions should remain on hold until the customer
          completes independent, transaction-specific verification through a
          separate trusted channel.
        </p>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-white">
                Transaction Details
              </h2>
              <button
                onClick={() => setSelected(null)}
                className="text-slate-400 hover:text-white"
                aria-label="Close transaction details"
              >
                <X size={21} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500">Transaction ID</p>
                <p className="text-cyan-400 font-medium mt-1">{selected.id}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Customer</p>
                  <p className="text-white mt-1">{selected.customer}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Amount</p>
                  <p className="text-white font-semibold mt-1">
                    ₹{selected.amount.toLocaleString('en-IN')}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Beneficiary</p>
                  <p className="text-white mt-1">{selected.beneficiary}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Time</p>
                  <p className="text-white mt-1">{selected.time}</p>
                </div>
              </div>

              <div className="rounded-lg bg-slate-950 p-3">
                <p className="text-xs text-slate-500">Security notes</p>
                <p className="text-sm text-slate-300 mt-1">
                  {selected.reason}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-2">Current status</p>
                <span
                  className={`inline-flex rounded-full border px-3 py-1 text-xs ${statusStyle(selected.status)}`}
                >
                  {selected.status}
                </span>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                {selected.status !== 'On Hold' && (
                  <button
                    onClick={() => updateStatus(selected.id, 'On Hold')}
                    className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/20"
                  >
                    <Lock size={16} />
                    Place on Hold
                  </button>
                )}

                {selected.status === 'On Hold' && (
                  <button
                    onClick={() => updateStatus(selected.id, 'Pending')}
                    className="flex items-center gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 px-4 py-2.5 text-sm text-amber-400 hover:bg-amber-500/20"
                  >
                    <Unlock size={16} />
                    Return to Pending
                  </button>
                )}
              </div>

              <p className="text-xs text-slate-500">
                Demo only: these controls change the displayed sample status.
                They do not authorize, hold, or release a real payment.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Transactions
