import { expect, test } from "@playwright/test";

test("a visitor can search, rate a movie, and get a model explanation", async ({ page }) => {
  await page.route("http://localhost:8000/api/v1/genres", (route) =>
    route.fulfill({ json: ["Drama", "Sci-Fi"] }),
  );
  await page.route(/http:\/\/localhost:8000\/api\/v1\/movies/, (route) =>
    route.fulfill({
      json: {
        total: 1,
        items: [{ movie_id: 11, title: "Arrival (2016)", genres: ["Drama", "Sci-Fi"] }],
      },
    }),
  );
  await page.route("http://localhost:8000/api/v1/recommendations", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      ratings: [{ movie_id: 11, rating: 5 }],
      limit: 10,
    });
    await route.fulfill({
      json: [
        {
          movie_id: 12,
          title: "Dune (2021)",
          genres: ["Drama", "Sci-Fi"],
          estimated_rating: 4.6,
          reason: "Shares Sci-Fi with a film you rated highly.",
        },
      ],
    });
  });

  await page.goto("/");
  await page.getByRole("textbox", { name: "Search movies" }).fill("Arrival");
  await page.getByRole("button", { name: "5 out of 5: Loved it" }).click();
  await page.getByRole("button", { name: "Find my next film" }).click();

  await expect(page.getByRole("heading", { name: "Dune (2021)" })).toBeVisible();
  await expect(page.getByText("Shares Sci-Fi with a film you rated highly.")).toBeVisible();
});
