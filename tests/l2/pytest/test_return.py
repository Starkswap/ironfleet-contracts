import pytest
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.public.abi import get_selector_from_name

from conftest import L1_CONTRACT_ADDRESS

FINALISED = 0
OPEN = 1
AT_SEA = 2
RETURNED = 3

L1_HANDLER_SELECTOR = get_selector_from_name("process_msg_from_l1")


@pytest.mark.parametrize(
    "ships,finalisations",
    [
        # Test configuration in the form of
        # ( [ departed ships ], array of finalisations in the form of [[amounts to finalize], total_payout, (user_payout_balance, oldest active ship, active ships count)]
        ([200], [([200], 30, (30, 2, 0))]),   # single ship finalized in one go
        ([200, 250], [([200, 250], 30, (29, 3, 0))]),   # 2 ships get finalized in one go
        ([200, 200], [([200, 200], 30, (30, 3, 0))]),   # 2 ships same amount get finalized in one go
        ([200, 250], [([200], 30, (30, 2, 1)), ([250], 30, (60, 3, 0))]),  # 2 ships different amounts finalized inorder separately
        ([200, 200], [([200], 30, (30, 2, 1)), ([200], 30, (60, 3, 0))]),  # 2 ships same amount get finalized separately in the right order
        ([200, 250], [([250], 30, (30, 1, 1)), ([200], 30, (60, 3, 0))]),  # 2 ships different amounts separately finalized reverse order
        ([200, 250, 300], [([250], 30, (30, 1, 2)), ([300], 30, (60, 1, 1)),([200], 30, (90, 4, 0))]), # 3 ships finalized separately in random order
        ([200, 250, 300], [([300, 250], 30, (29, 1, 1)), ([200], 30, (59, 4, 0))]), # 3 ships finalized out of order in batch of 2 and one separately
        ([200, 250, 300], [([300, 200], 30, (30, 2, 1)), ([250], 30, (60, 4, 0))]) # 3 ships finalized out of order in batch of 2 and one separately
    ],
    ids=[
        "Single ship finalized",
        "Two ships finalized atomically inorder",
        "Two ships same amount finalized atomically inorder",
        "Two ships finalized separately inorder",
        "Two ships same amount finalized separately inorder",
        "Two ships finalized separately reverse order",
        "Three ships finalized separately random order",
        "Three ships finalized separately batch of 2 then 1",
        "Three ships finalized separately batch of 2 with gap then 1"
    ]
)
class TestFinalizeHasBalance:

    @pytest.mark.asyncio
    async def test_finalize_enough_balance(self, starknet: Starknet, admiral, cargo_token, loot_token, l2_keeper, user1, ships, finalisations):
        await l2_keeper.mint(cargo_token, user1, 2000)
        await user1.approve(cargo_token, admiral.contract_address, 5000)

        fleet_size = 0
        for deposit in ships:
            print(f"Depositing {deposit} into ship and departing")
            await user1.deposit_into_ship(admiral, deposit)
            await l2_keeper.depart(admiral, fleet_size + 1)
            fleet_size += 1

        for finalisation in finalisations:
            (amounts, payout, (user_payout_balance, oldest_active_idx, active_count)) = finalisation

            await l2_keeper.mint(loot_token, admiral, payout)
            print(f"Finalising amounts {amounts} with total payout {payout}")
            payload = build_l1_message_handler_payload(amounts, payout)

            await starknet.send_message_to_l2(L1_CONTRACT_ADDRESS, admiral.contract_address, L1_HANDLER_SELECTOR, payload)
            for amount in amounts:
                ship_idx = ships.index(amount)
                print(f"Finalising ship {ship_idx+1}")
                await admiral.unload_ship(ship_idx+1).invoke()
                ships[ship_idx] = -1

            print(f"Checking user has received {user_payout_balance} and that the oldest active ship is {oldest_active_idx} with {active_count} active ships")
            user1Payout = await loot_token.balanceOf(user1.contract_address).call()
            assert user1Payout.result.balance.low == user_payout_balance
            await check_ships_indices(admiral, oldest_active_idx, active_count)

@pytest.mark.parametrize(
    "ships,return_messages,finalisations",
    [
        # Test configuration in the form of
        # (
        #   [ departed ships ],
        #   [ (total_loot), [returned_ships] ]
        #   [ (looot_top_up, finalise_ship) ]
        # )
        ([200], [(50, [200])], [(50, [200])]),
        ([100, 300], [(40, [100, 300])], [(10, [100])]),
        ([300, 100], [(40, [300, 100])], [(40,[300, 100])]),
        ([300, 100, 200], [(60, [300, 100, 200])], [(60,[300, 100, 200])]),
    ],
    ids=[
        "Single ship then unload_ship",
        "Two ships, both return, finalise one",
        "Two ships, both return, finalise both",
        "Three ships, all return, finalise all",
    ]
)
class TestReturn:

    @pytest.mark.asyncio
    async def test_finalize_insufficient_balance(self, starknet: Starknet, admiral, cargo_token, loot_token, l2_keeper, user1, ships, return_messages, finalisations):
        await l2_keeper.mint(cargo_token, user1, 2000)
        await user1.approve(cargo_token, admiral.contract_address, 5000)

        fleet = []
        for deposit in ships:
            print(f"Depositing {deposit} into ship and departing")
            await user1.deposit_into_ship(admiral, deposit)
            await l2_keeper.depart(admiral, len(fleet) + 1)
            fleet.append({'cargo': deposit, 'status': AT_SEA})

        for(loot, amounts) in return_messages:
            print(f"Processing return for ships {amounts} with loot {loot}")

            payload = build_l1_message_handler_payload(amounts, loot)
            await starknet.send_message_to_l2(L1_CONTRACT_ADDRESS, admiral.contract_address, L1_HANDLER_SELECTOR, payload)

            total_cargo_shipped = sum(amounts)
            for cargo_returned in amounts:
                fleet[ships.index(cargo_returned)]['loot'] = (loot * cargo_returned)/total_cargo_shipped
                fleet[ships.index(cargo_returned)]['status'] = RETURNED

        print(f"Fleet: {fleet}")
        user_loot_balance = 0
        for (topup, amounts) in finalisations:
            print(f"Processing finalise for ships {amounts} with loot topup of {topup}")

            print(f"Minting {topup} loot into Conductor")
            await l2_keeper.mint(loot_token, admiral, topup)

            for amount in amounts:
                ship_idx = ships.index(amount)+1
                print(f"Trying to finalize ship {ship_idx}")
                res = await admiral.unload_ship(ship_idx).invoke()
                if res.result.success == 1:
                    user_loot_balance = user_loot_balance + fleet[ship_idx-1]['loot']
                    fleet[ship_idx-1]['status'] = FINALISED

            print(f"Fleet: {fleet}")
            print(f"Check user balance is {user_loot_balance}")
            user1Payout = await loot_token.balanceOf(user1.contract_address).call()
            assert user1Payout.result.balance.low == user_loot_balance

            open_ship_idx = len(fleet) + 1
            oldest_active_ship_idx = open_ship_idx
            active_ships = 0
            i = 1
            for s in fleet:
                if s['status'] == AT_SEA:
                    active_ships += 1

                if s['status'] == AT_SEA or s['status'] == RETURNED:
                    if i < open_ship_idx:
                        oldest_active_ship_idx = i
                i+=1

            res = await admiral.get_fleet().call()
            print(f"===> {res.result}")

            print(f"Open ship: {open_ship_idx}, oldest ship: {oldest_active_ship_idx}, at_sea: {active_ships}")
            await check_ships_indices(admiral, oldest_active_ship_idx, active_ships)

@pytest.mark.asyncio
async def test_finalise_exceed_batch_size(starknet, admiral, cargo_token, l2_keeper, loot_token, user1, user2, user3):
    print(f"Setup")
    await l2_keeper.send_transaction(admiral.contract_address, 'set_unload_batch_size', calldata=[2])
    await l2_keeper.mint(cargo_token, user1, 2000)
    await l2_keeper.mint(cargo_token, user2, 2000)
    await l2_keeper.mint(cargo_token, user3, 2000)
    await user1.approve(cargo_token, admiral.contract_address, 5000)
    await user2.approve(cargo_token, admiral.contract_address, 5000)
    await user3.approve(cargo_token, admiral.contract_address, 5000)

    print(f"Deposit from three users")
    await user1.deposit_into_ship(admiral, 150)
    await user2.deposit_into_ship(admiral, 200)
    await user3.deposit_into_ship(admiral, 500)

    print(f"Depart ship")
    await l2_keeper.depart(admiral, 1)

    print(f"Send return ship message ")
    await l2_keeper.mint(loot_token, admiral, 300)
    await starknet.send_message_to_l2(L1_CONTRACT_ADDRESS, admiral.contract_address, L1_HANDLER_SELECTOR, [1, 850, 0, 300, 0, 42, 0])

    res = await admiral.get_ship_status(1).call()
    print(f"Ship 1 details: {res.result}")
    assert len(res.result.crew) == 3
    assert res.result.status == RETURNED

    await admiral.unload_ship(1).invoke()

    u1_balance = await loot_token.balanceOf(user1.contract_address).call()
    u2_balance = await loot_token.balanceOf(user2.contract_address).call()
    u3_balance = await loot_token.balanceOf(user3.contract_address).call()

    assert u1_balance.result.balance.low == 0
    assert u2_balance.result.balance.low == 70
    assert u3_balance.result.balance.low == 176

    res = await admiral.get_ship_status(1).call()
    print(f"Ship 1 details: {res.result}")
    assert len(res.result.crew) == 1
    assert res.result.status == RETURNED

    await admiral.unload_ship(1).invoke()

    res = await admiral.get_ship_status(1).call()
    print(f"Ship 1 details: {res.result}")
    assert len(res.result.crew) == 0
    assert res.result.status == FINALISED

    u1_balance = await loot_token.balanceOf(user1.contract_address).call()
    u2_balance = await loot_token.balanceOf(user2.contract_address).call()
    u3_balance = await loot_token.balanceOf(user3.contract_address).call()

    assert u1_balance.result.balance.low == 52
    assert u2_balance.result.balance.low == 70
    assert u3_balance.result.balance.low == 176

@pytest.mark.asyncio
async def test_finalise_less_than_batch_size(starknet, admiral, cargo_token, l2_keeper, loot_token, user1, user2, user3):
    print(f"Setup")
    await l2_keeper.mint(cargo_token, user1, 2000)
    await l2_keeper.mint(cargo_token, user2, 2000)
    await l2_keeper.mint(cargo_token, user3, 2000)
    await user1.approve(cargo_token, admiral.contract_address, 5000)
    await user2.approve(cargo_token, admiral.contract_address, 5000)
    await user3.approve(cargo_token, admiral.contract_address, 5000)

    print(f"Deposit from three users")
    await user1.deposit_into_ship(admiral, 150)
    await user2.deposit_into_ship(admiral, 200)
    await user3.deposit_into_ship(admiral, 500)

    print(f"Depart ship")
    await l2_keeper.depart(admiral, 1)

    print(f"Send return ship message ")
    await l2_keeper.mint(loot_token, admiral, 300)
    await starknet.send_message_to_l2(L1_CONTRACT_ADDRESS, admiral.contract_address, L1_HANDLER_SELECTOR, [1, 850, 0, 300, 0, 42, 0])

    res = await admiral.get_ship_status(1).call()
    print(f"Ship 1 details: {res.result}")
    assert len(res.result.crew) == 3
    assert res.result.status == RETURNED

    await admiral.unload_ship(1).invoke()

    res = await admiral.get_ship_status(1).call()
    print(f"Ship 1 details: {res.result}")
    assert len(res.result.crew) == 0
    assert res.result.status == FINALISED

    u1_balance = await loot_token.balanceOf(user1.contract_address).call()
    u2_balance = await loot_token.balanceOf(user2.contract_address).call()
    u3_balance = await loot_token.balanceOf(user3.contract_address).call()

    assert u1_balance.result.balance.low == 52
    assert u2_balance.result.balance.low == 70
    assert u3_balance.result.balance.low == 176

async def check_ships_indices(admiral, oldest_idx: int, active_count: int):
    oldest_active_idx = await admiral.get_oldest_active_ship_idx().call()
    active_ships_count = await admiral.get_fleet_size().call()
    assert oldest_active_idx.result.ship_idx == oldest_idx
    assert active_ships_count.result.count == active_count


def build_l1_message_handler_payload(amounts: list[int], payout: int):
    payload = [len(amounts)]
    for x in amounts:
        payload.append(x)
        payload.append(0)
    payload.append(payout)
    payload.append(0)
    payload.append(37000) # Gas Used
    payload.append(0)


    return payload
