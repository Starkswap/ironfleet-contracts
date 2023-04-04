%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.uint256 import (Uint256, uint256_add)

@constructor
func constructor{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(a: felt):
    return ()
end


@storage_var
func sv_transfers(recipient: felt) -> (amount: Uint256):
end

@external
func initiate_withdraw{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(l1_recipient: felt, amount: Uint256):

    let (balance: Uint256) = sv_transfers.read(l1_recipient)
    let (new_balance: Uint256, is_overflow) = uint256_add(balance, amount)
    assert is_overflow = 0

    sv_transfers.write(l1_recipient, new_balance)

    return ()
end

@external
func burn{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(l1_recipient: felt):
    sv_transfers.write(l1_recipient, Uint256(0,0))
    return ()
end


@view
func balance{syscall_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr}(l1_recipient: felt) -> (balance: Uint256):
    let (balance: Uint256) = sv_transfers.read(l1_recipient)
    return (balance)
end
