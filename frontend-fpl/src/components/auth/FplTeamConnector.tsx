import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useState } from "react"

export function FplTeamConnector() {
  const [teamName, setTeamName] = useState("")

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (!teamName.trim()) {
      alert("Please enter your team name.")
      return
    }
    console.log("Team name submitted:", teamName)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Enter Your FPL Team Name</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid gap-2">
            <Label htmlFor="team-name">Team Name</Label>
            <Input
              id="team-name"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="pepBall"
              required
            />
          </div>
          <Button type="submit" className="w-full p-3.5">
            Continue
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
