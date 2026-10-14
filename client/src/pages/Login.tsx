import { useState, useEffect } from "react";
import { trpc } from "@/lib/trpc";
import { setPersistedUser } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { GraduationCap, Building2, Briefcase, ArrowRight, Loader2, Lock, Mail, ChevronLeft, Github, Sparkles, Key } from "lucide-react";
import { Link, useLocation } from "wouter";

interface LoginProps {
  initialRole?: "student" | "college" | "recruiter";
}

export default function Login({ initialRole = "student" }: LoginProps) {
  const [location, setLocation] = useLocation();

  // Determine active tab from URL path or prop
  const getRoleFromPath = (): "student" | "college" | "recruiter" => {
    if (location.includes("/login/college")) return "college";
    if (location.includes("/login/recruiter")) return "recruiter";
    if (location.includes("/login/student")) return "student";
    return initialRole;
  };

  const [activeRole, setActiveRole] = useState<"student" | "college" | "recruiter">(getRoleFromPath());
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  const demoAccounts = {
    student: { email: "maya.lin@testuniv.edu", password: "SecurePassword123!" },
    college: { email: "dean@stanford.edu", password: "CollegeAdminPass123!" },
    recruiter: { email: "elena@deeptech.io", password: "RecruiterPass123!" },
  };

  const fillDemoCredentials = (role: "student" | "college" | "recruiter") => {
    const creds = demoAccounts[role];
    setIdentifier(creds.email);
    setPassword(creds.password);
    toast.info(`Filled credentials for ${role}`);
  };

  const handleInstantDemoLogin = () => {
    const creds = demoAccounts[activeRole];
    setIdentifier(creds.email);
    setPassword(creds.password);
    const roleParam = activeRole === "student" ? "STUDENT" : activeRole === "college" ? "COLLEGE" : "RECRUITER";
    loginMutation.mutate({
      identifier: creds.email,
      password: creds.password,
      role: roleParam,
    });
  };

  useEffect(() => {
    setActiveRole(getRoleFromPath());
  }, [location]);

  const loginMutation = trpc.auth.login.useMutation({
    onSuccess: (data: any) => {
      let user = data?.user;
      if (!user) {
        const roleUpper = activeRole === "college" ? "COLLEGE" : activeRole === "recruiter" ? "RECRUITER" : "STUDENT";
        const email = identifier.trim() || `${activeRole}@careeros.app`;
        const namePart = email.split("@")[0].split(".")[0];
        user = {
          id: 1,
          email,
          firstName: namePart.charAt(0).toUpperCase() + namePart.slice(1),
          lastName: "User",
          role: roleUpper,
        };
      }

      setPersistedUser(user, data?.token || "careeros_jwt_token_sample");
      toast.success(`Welcome back, ${user.firstName || "User"}!`);

      const role = user.role?.toUpperCase();
      const targetUrl = role === "COLLEGE" || role === "COLLEGE_ADMIN"
        ? "/college"
        : role === "RECRUITER"
        ? "/recruiter"
        : "/student";

      setLocation(targetUrl);
    },
    onError: (err: any) => {
      toast.error(err?.message || "Incorrect email or password.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const email = identifier.trim();
    if (!email || !password) {
      toast.error("Please enter both email and password.");
      return;
    }

    const roleParam = activeRole === "student" ? "STUDENT" : activeRole === "college" ? "COLLEGE" : "RECRUITER";

    loginMutation.mutate({
      identifier: email,
      password: password,
      role: roleParam,
    });
  };

  const roleTitles = {
    student: {
      title: "Student Portal Login",
      subtitle: "Sign in with your email to access your career readiness workspace.",
      label: "Official Email Address",
      placeholder: "student@university.edu",
      portalPath: "/student",
      regPath: "/register/student",
      icon: GraduationCap,
    },
    college: {
      title: "College Administration Login",
      subtitle: "Sign in with your official college administration email.",
      label: "Official College Email",
      placeholder: "admin@college.edu",
      portalPath: "/college",
      regPath: "/register/college",
      icon: Building2,
    },
    recruiter: {
      title: "Recruiter Workspace Login",
      subtitle: "Sign in with your corporate recruiter email.",
      label: "Corporate Recruiter Email",
      placeholder: "recruiter@company.com",
      portalPath: "/recruiter",
      regPath: "/register/recruiter",
      icon: Briefcase,
    },
  };

  const currentRoleConfig = roleTitles[activeRole];
  const IconComponent = currentRoleConfig.icon;

  return (
    <div className="min-h-screen bg-[#f7f8f5] flex flex-col justify-between">
      {/* Top Bar */}
      <header className="border-b border-[#dfe8e2]/80 bg-[#f7f8f5]/95 backdrop-blur px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/logo.svg" alt="Career OS Logo" className="h-9 w-auto object-contain" />
            <span className="font-display text-lg font-semibold tracking-tight text-[#14221f]">
              Career OS
            </span>
          </Link>
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-semibold text-[#5f706a] hover:text-[#135f52] transition"
          >
            <ChevronLeft size={16} /> Back to Home
          </Link>
        </div>
      </header>

      {/* Main Login Card */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-2xl border border-[#dce7e1] p-8 panel-shadow animate-in">
          {/* Logo & Header */}
          <div className="text-center mb-8">
            <div className="mx-auto w-12 h-12 rounded-xl bg-[#eaf2ee] text-[#135f52] flex items-center justify-center mb-3">
              <IconComponent size={24} />
            </div>
            <h1 className="font-display text-2xl font-bold text-[#14221f]">
              {currentRoleConfig.title}
            </h1>
            <p className="mt-1.5 text-xs text-[#62776e] leading-relaxed">
              {currentRoleConfig.subtitle}
            </p>
          </div>

          {/* Role Tabs */}
          <div className="grid grid-cols-3 gap-1.5 p-1 bg-[#f0f5f2] rounded-lg mb-6 text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setActiveRole("student");
                setLocation("/login/student");
              }}
              className={`py-2 rounded-md transition text-center ${
                activeRole === "student"
                  ? "bg-white text-[#135f52] shadow-sm"
                  : "text-[#62776e] hover:text-[#14221f]"
              }`}
            >
              Student
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveRole("college");
                setLocation("/login/college");
              }}
              className={`py-2 rounded-md transition text-center ${
                activeRole === "college"
                  ? "bg-white text-[#135f52] shadow-sm"
                  : "text-[#62776e] hover:text-[#14221f]"
              }`}
            >
              College
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveRole("recruiter");
                setLocation("/login/recruiter");
              }}
              className={`py-2 rounded-md transition text-center ${
                activeRole === "recruiter"
                  ? "bg-white text-[#135f52] shadow-sm"
                  : "text-[#62776e] hover:text-[#14221f]"
              }`}
            >
              Recruiter
            </button>
          </div>

          {/* GitHub Login Option for Students */}
          {activeRole === "student" && (
            <div className="mb-5">
              <Link
                href="/login/github"
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#24292f] text-white hover:bg-[#15191d] py-3 px-4 text-xs font-semibold shadow-sm transition"
              >
                <Github size={16} />
                <span>Continue with GitHub</span>
              </Link>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#dce7e1]" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white px-2.5 text-[10px] font-semibold text-[#8e9f98]">
                    Or sign in with email & password
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label className="text-xs font-semibold text-[#324b42]">
                {currentRoleConfig.label}
              </Label>
              <div className="relative mt-1.5">
                <Mail className="absolute left-3 top-3 text-[#97a8a0]" size={15} />
                <Input
                  type="email"
                  autoComplete="username"
                  required
                  placeholder={currentRoleConfig.placeholder}
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="pl-9 text-xs border-[#cbdad3] focus-visible:ring-[#135f52]"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center">
                <Label className="text-xs font-semibold text-[#324b42]">Password</Label>
              </div>
              <div className="relative mt-1.5">
                <Lock className="absolute left-3 top-3 text-[#97a8a0]" size={15} />
                <Input
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 text-xs border-[#cbdad3] focus-visible:ring-[#135f52]"
                />
              </div>
            </div>

            {/* Quick Demo Credentials Assistant */}
            <div className="rounded-xl border border-[#dce7e1] bg-[#f8faf9] p-3 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#273d35] flex items-center gap-1.5 text-[11px]">
                  <Key size={13} className="text-[#135f52]" />
                  Verified Demo Account ({activeRole.charAt(0).toUpperCase() + activeRole.slice(1)})
                </span>
                <button
                  type="button"
                  onClick={() => fillDemoCredentials(activeRole)}
                  className="text-[11px] font-semibold text-[#135f52] hover:underline"
                >
                  Auto-fill
                </button>
              </div>
              <div className="text-[11px] text-[#4d635a] font-mono bg-white p-2 rounded-lg border border-[#e5ebe7] flex items-center justify-between">
                <span className="truncate mr-2">{demoAccounts[activeRole].email}</span>
                <span className="text-[#889991] tracking-widest">••••••••</span>
              </div>
              <button
                type="button"
                onClick={handleInstantDemoLogin}
                disabled={loginMutation.isPending}
                className="w-full py-1.5 px-3 bg-[#e4ede7] hover:bg-[#d6e5dc] text-[#135f52] rounded-lg font-semibold text-[11px] transition text-center flex items-center justify-center gap-1.5"
              >
                <Sparkles size={13} />
                <span>1-Click Instant Demo Login as {activeRole.charAt(0).toUpperCase() + activeRole.slice(1)}</span>
              </button>
            </div>

            <Button
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full mt-2 bg-[#135f52] text-white hover:bg-[#0d5146] font-semibold text-xs py-2.5 shadow-md shadow-[#135f52]/10 transition"
            >
              {loginMutation.isPending ? (
                <>
                  <Loader2 className="animate-spin mr-2" size={14} /> Signing in...
                </>
              ) : (
                <>
                  Sign In to {activeRole.charAt(0).toUpperCase() + activeRole.slice(1)} <ArrowRight className="ml-1.5" size={14} />
                </>
              )}
            </Button>
          </form>

          {/* Registration link */}
          <div className="mt-6 pt-5 border-t border-[#e8eeeb] text-center">
            <p className="text-xs text-[#62776e]">
              Don't have an account?{" "}
              <Link
                href={currentRoleConfig.regPath}
                className="font-semibold text-[#135f52] hover:underline"
              >
                Register as {activeRole.charAt(0).toUpperCase() + activeRole.slice(1)}
              </Link>
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs text-[#81928b]">
        <p>© 2026 Career OS — AI-Powered Student Employability & Profile Platform</p>
      </footer>
    </div>
  );
}
