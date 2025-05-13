import time
import threading
import asyncio

class TokenBucketRateLimiter:
    """
    A simple thread-safe token bucket rate limiter.
    """
    def __init__(self, tokens_per_second, max_tokens):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_refill_time = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens=1):
        """
        Consume tokens from the bucket. Returns True if successful, False otherwise.
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def consume_async(self, tokens=1):
        """
        Asynchronously consume tokens from the bucket. Waits if necessary.
        """
        # This is a simplified async version. A real async rate limiter
        # would use asyncio.sleep and potentially an async lock.
        # For now, we'll just use the synchronous consume and a simple sleep.
        # In a production async app, you'd use an async-compatible library.
        while True:
            with self.lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            # If not enough tokens, wait a bit before retrying
            await asyncio.sleep(1.0 / self.tokens_per_second if self.tokens_per_second > 0 else 0.1)


    def _refill(self):
        """
        Refill the bucket with new tokens based on time passed.
        """
        now = time.time()
        time_passed = now - self.last_refill_time
        new_tokens = time_passed * self.tokens_per_second
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill_time = now

# Example Usage (for testing the rate limiter itself)
if __name__ == '__main__':
    # Create a rate limiter that allows 2 tokens per second, with a max of 5 tokens
    limiter = TokenBucketRateLimiter(tokens_per_second=2, max_tokens=5)

    print("Attempting to consume 3 tokens...")
    if limiter.consume(3):
        print("Consumed 3 tokens successfully.")
    else:
        print("Failed to consume 3 tokens (rate limited).")

    print("Attempting to consume 3 tokens again...")
    if limiter.consume(3):
        print("Consumed 3 tokens successfully.")
    else:
        print("Failed to consume 3 tokens (rate limited).")

    print("Waiting for 2 seconds...")
    time.sleep(2)

    print("Attempting to consume 3 tokens after waiting...")
    if limiter.consume(3):
        print("Consumed 3 tokens successfully.")
    else:
        print("Failed to consume 3 tokens (rate limited).")

    # Example of async usage (requires running in an async context)
    # async def test_async_consume():
    #     print("\n--- Async Consume Test ---")
    #     async_limiter = TokenBucketRateLimiter(tokens_per_second=1, max_tokens=3)
    #     print("Attempting to consume 2 tokens asynchronously...")
    #     await async_limiter.consume_async(2)
    #     print("Consumed 2 tokens asynchronously.")
    #     print("Attempting to consume 2 tokens asynchronously again (should wait)...")
    #     await async_limiter.consume_async(2)
    #     print("Consumed 2 tokens asynchronously after waiting.")

    # import asyncio
    # asyncio.run(test_async_consume())