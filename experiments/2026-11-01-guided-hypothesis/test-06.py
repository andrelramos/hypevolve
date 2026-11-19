import timeit
import json
import random
from tornado.concurrent import Future


def setup():
    """
    Setup a realistic workload for testing Future.set_exception.
    In this test, we simulate a scenario where a large number of asynchronous
    tasks (represented by futures) encounter errors.

    We generate a list of error messages as might be produced in a real application.
    A fixed random seed is used for reproducibility.
    """
    random.seed(42)
    num_errors = 10000  # realistic scale for performance testing
    # Create a list of error messages that simulate real error details.
    error_messages = [f"Error occurred: {i}" for i in range(num_errors)]
    return error_messages


def experiment(error_messages):
    """
    Perform a real-world experiment that uses Future.set_exception.

    For each error message in the provided workload, the experiment:
      - Creates a Tornado Future.
      - Sets an exception (a ValueError with the error message) on the Future.
      - Retrieves the exception from the Future to simulate downstream error handling.

    The experiment returns a summary dictionary of:
      - 'num_futures': Number of futures processed.
      - 'last_exception': The string representation of the exception in the final Future.

    This mimics a realistic heavy-use scenario for asynchronous error propagation.
    """
    last_exception = None
    for msg in error_messages:
        fut = Future()
        # Performance-critical API call under test.
        fut.set_exception(ValueError(msg))
        # In realistic usage, downstream code would retrieve the exception.
        exc = fut.exception()
        # Assert the exception is of the expected type.
        assert isinstance(exc, ValueError), "Expected a ValueError instance."
        last_exception = str(exc)
    result_summary = {
        "num_futures": len(error_messages),
        "last_exception": last_exception,
    }
    return result_summary


def store_result(result, filename):
    """
    Store the reference result in a JSON file.

    The result is expected to be a dictionary with simple data types.
    """
    with open(filename, "w") as f:
        json.dump(result, f)


def load_result(filename):
    """
    Load the reference result from a JSON file.

    The result will be a dictionary used for equivalence checking.
    """
    with open(filename, "r") as f:
        result = json.load(f)
    return result


def check_equivalence(reference_result, current_result):
    """
    Check that the current result of experiment() is equivalent to the stored reference result.

    The equivalence checks assert that:
      - The number of futures processed matches.
      - The final exception message matches.
    """
    assert (
        reference_result["num_futures"] == current_result["num_futures"]
    ), f"Expected {reference_result['num_futures']} futures, got {current_result['num_futures']}"
    assert (
        reference_result["last_exception"] == current_result["last_exception"]
    ), f"Expected last exception '{reference_result['last_exception']}', got '{current_result['last_exception']}'"


def run_test(eqcheck: bool = False, reference: bool = False, prefix: str = "") -> float:
    """
    Run the performance test of Future.set_exception.

    Steps:
      1. Setup the workload (not timed).
      2. Time the `experiment` function, which creates a number of Futures,
         sets exceptions on them, and gathers a summary result.
      3. If reference is True, store the result as the reference.
      4. If eqcheck is True, load the reference result and check equivalence against
         the current result.
      5. Return the execution time.

    The timeit template is assumed to return a tuple: (execution_time, result)
    """
    workload = setup()
    # Time the experiment over a single complete run.
    execution_time, result = timeit.timeit(lambda: experiment(workload), number=1)

    if reference:
        store_result(result, f"{prefix}_result.json")
    if eqcheck:
        ref_result = load_result(f"{prefix}_result.json")
        check_equivalence(ref_result, result)
    return execution_time


timeit.template = """
def inner(_it, _timer{init}):
    {setup}
    _t0 = _timer()
    for _i in _it:
        retval = {stmt}
    _t1 = _timer()
    return _t1 - _t0, retval
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Measure performance of API.")
    parser.add_argument(
        "output_file", type=str, help="File to append timing results to."
    )
    parser.add_argument(
        "--eqcheck", action="store_true", help="Enable equivalence checking"
    )
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Store result as reference instead of comparing",
    )
    parser.add_argument(
        "--file_prefix",
        type=str,
        help="Prefix for any file where reference results are stored",
    )
    args = parser.parse_args()

    # Measure the execution time
    execution_time = run_test(args.eqcheck, args.reference, args.file_prefix)

    # Append the results to the specified output file
    with open(args.output_file, "a") as f:
        f.write(f"Execution time: {execution_time:.6f}s\n")


if __name__ == "__main__":
    main()


timeit.template = """
def inner(_it, _timer{init}):
    {setup}
    _t0 = _timer()
    for _i in _it:
        retval = {stmt}
    _t1 = _timer()
    return _t1 - _t0, retval
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Measure performance of API.')
    parser.add_argument('output_file', type=str, help='File to append timing results to.')
    parser.add_argument('--eqcheck', action='store_true', help='Enable equivalence checking')
    parser.add_argument('--reference', action='store_true', help='Store result as reference instead of comparing')
    parser.add_argument('--file_prefix', type=str, help='Prefix for any file where reference results are stored')
    args = parser.parse_args()

    # Measure the execution time
    execution_time = run_test(args.eqcheck, args.reference, args.file_prefix)

    # Append the results to the specified output file
    with open(args.output_file, 'a') as f:
        f.write(f'Execution time: {execution_time:.6f}s\n')

if __name__ == '__main__':
    main()
