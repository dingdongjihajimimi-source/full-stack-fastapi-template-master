import { Link, useNavigate } from "@tanstack/react-router"
import { useEffect } from "react"
import { Button } from "@/components/ui/button"

const ErrorComponent = () => {
  const navigate = useNavigate()

  useEffect(() => {
    // If there's a stored token but we're on the error page,
    // it's likely the token is invalid. Clear it and redirect to login.
    const token = localStorage.getItem("access_token")
    if (token) {
      localStorage.removeItem("access_token")
      navigate({ to: "/login" })
    }
  }, [navigate])

  return (
    <div
      className="flex min-h-screen items-center justify-center flex-col p-4"
      data-testid="error-component"
    >
      <div className="flex items-center z-10">
        <div className="flex flex-col ml-4 items-center justify-center p-4">
          <span className="text-6xl md:text-8xl font-bold leading-none mb-4">
            Error
          </span>
          <span className="text-2xl font-bold mb-2">Oops!</span>
        </div>
      </div>

      <p className="text-lg text-muted-foreground mb-4 text-center z-10">
        Something went wrong. Please try again.
      </p>
      <Link to="/">
        <Button>Go Home</Button>
      </Link>
    </div>
  )
}

export default ErrorComponent
