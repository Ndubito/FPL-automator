
import { BrowserRouter, Routes, Route } from "react-router-dom"
// import Home from "@/pages/Home"
import Login from "@/pages/auth/Login"
import Signup from "@/pages/auth/Signup"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* <Route path="/" element={<Home />} /> */}
        <Route path="/" element={<Login />} />
         <Route path="/register" element={<Signup />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
