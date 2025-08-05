"use client"
import { useState } from "react"
import { SignupForm } from "@/components/auth/SignupForm"
import { FplTeamConnector } from "@/components/auth/FplTeamConnector"

export default function Page() {
  const [step, setStep] = useState<"signup" | "fpl">("signup")

  return (
    <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <div className="w-full max-w-sm">
        {step === "signup" ? (
          <SignupForm onSignup={() => setStep("fpl")} />
        ) : (
          <FplTeamConnector />
        )}
      </div>
    </div>
  )
}
