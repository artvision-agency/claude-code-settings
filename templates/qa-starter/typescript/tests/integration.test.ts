import { beforeEach, describe, expect, it, vi } from "vitest";

// Example service with injected HTTP client (easy to mock).
interface HttpClient {
  get(url: string): Promise<{ status: number; json: () => Promise<unknown> }>;
  post(url: string, body: unknown): Promise<{ status: number; json: () => Promise<unknown> }>;
}

class UserService {
  constructor(private readonly http: HttpClient) {}

  async getUser(id: number): Promise<{ id: number; name: string }> {
    const resp = await this.http.get(`/users/${id}`);
    if (resp.status !== 200) throw new Error(`status ${resp.status}`);
    return (await resp.json()) as { id: number; name: string };
  }

  async createUser(name: string): Promise<number> {
    const resp = await this.http.post("/users", { name });
    if (resp.status !== 201) throw new Error(`status ${resp.status}`);
    const { id } = (await resp.json()) as { id: number };
    return id;
  }
}

describe("UserService", () => {
  let http: HttpClient;
  let svc: UserService;

  beforeEach(() => {
    http = {
      get: vi.fn(),
      post: vi.fn(),
    };
    svc = new UserService(http);
  });

  it("returns user on 200", async () => {
    vi.mocked(http.get).mockResolvedValue({
      status: 200,
      json: async () => ({ id: 42, name: "Alice" }),
    });

    const user = await svc.getUser(42);

    expect(user).toEqual({ id: 42, name: "Alice" });
    expect(http.get).toHaveBeenCalledWith("/users/42");
  });

  it("throws on non-200", async () => {
    vi.mocked(http.get).mockResolvedValue({ status: 500, json: async () => ({}) });
    await expect(svc.getUser(1)).rejects.toThrow(/status 500/);
  });

  it("creates and returns id", async () => {
    vi.mocked(http.post).mockResolvedValue({
      status: 201,
      json: async () => ({ id: 7 }),
    });

    await expect(svc.createUser("Bob")).resolves.toBe(7);
    expect(http.post).toHaveBeenCalledWith("/users", { name: "Bob" });
  });
});
