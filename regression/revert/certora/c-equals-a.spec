rule c_equals_a {
    env e;
    calldataarg args;
    f(e, args);
    assert(currentContract.c == currentContract.x);
}