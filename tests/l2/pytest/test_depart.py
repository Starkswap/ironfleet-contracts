import pytest
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.public.abi import get_selector_from_name

from open_zeppelin.utils import (uint)
from conftest import L1_CONTRACT_ADDRESS
L1_HANDLER_SELECTOR = get_selector_from_name("process_msg_from_l1")


@pytest.mark.parametrize(
    "ships_config",
    [
        [[200]],
        [[200, 50, 250]],
        [[200], [50, 250], [500, 10]],
    ],
    ids=[
        "single deposit single departure",
        "multiple deposits single departure",
        "multiple deposits multiple departure"
    ]
)
class TestDepartureSingleUser:

    @pytest.mark.asyncio
    async def test_depart_single_user(self, starknet: Starknet, admiral, cargo_token, starkgate, l2_keeper, user1, ships_config):
        await l2_keeper.mint(cargo_token, user1, 2000)
        await user1.approve(cargo_token, admiral.contract_address, 5000)
        total = 0
        fleet_size = 0

        for ship in ships_config:
            ship_cargo = 0

            for deposit in ship:
                ship_cargo += deposit
                print(f"Depositing {deposit} into ship for a ship total of {ship_cargo}")
                await user1.deposit_into_ship(admiral, deposit)

            total += ship_cargo

            await check_ship_details(admiral, ship_cargo, 1)

            print(f"Departing")
            await user1.depart(admiral, fleet_size + 1)
            fleet_size += 1

            await check_ship_details(admiral, 0, 0)

            print(f"Checking message was sent to L1")
            starknet.consume_message_from_l2(admiral.contract_address, L1_CONTRACT_ADDRESS, [ship_cargo, 0])

            print(f"Check active ships count is {fleet_size}")
            res = await admiral.get_fleet_size().call()
            assert res.result.count == fleet_size

            print(f"Check starkgate balance is {total}")
            res = await starkgate.balance(L1_CONTRACT_ADDRESS).call()
            assert res.result.balance == uint(total)


        print("Check oldest active ship idx is 1")
        res = await admiral.get_oldest_active_ship_idx().call()
        assert res.result.ship_idx == 1


@pytest.mark.parametrize(
    "ships_config",
    [
        [([(1,200), (2,50), (3,250)], (500,1,1))],
        [([(1,200), (2,50), (1,50), (3,250), (3,150)], (700,1,1))],
        [([(1,200), (2,50), (3,50)], (300,1,1)), ([(1,50), (3,100), (2,50)], (500,1,2))],
    ],
    ids=[
        "single departure single deposit per user",
        "single departure multiple deposits  per user",
        "two departure single deposit per user",
    ]
)
class TestDepartureMultipleUsers:

    @pytest.mark.asyncio
    async def test_three_users_single_deposits_single_departure(self, starknet, admiral, cargo_token, starkgate, l2_keeper, user1, user2, user3, ships_config):
        users = [user1, user2, user3]

        for u in users:
            await l2_keeper.mint(cargo_token, u, 5000)
            await u.approve(cargo_token, admiral.contract_address, 5000)


        for (deposits, (starkgate_balance, oldest_ship_idx, active_ships_count)) in ships_config:

            ship_cargo = 0
            contributors = set()
            for (user, deposit) in deposits:
                ship_cargo += deposit
                contributors.add(user)
                print(f"Depositing {deposit} for user {user}")
                await users[user-1].deposit_into_ship(admiral, deposit)

            ship_idx = await check_ship_details(admiral, ship_cargo, len(contributors))

            print(f"Departing")
            await users[deposits[0][0]].depart(admiral, ship_idx)
            await check_ships_indices(admiral, oldest_ship_idx, active_ships_count)

            print(f"Checking message was sent to L1")
            starknet.consume_message_from_l2(admiral.contract_address, L1_CONTRACT_ADDRESS, [ship_cargo, 0])

            print(f"Check starkgate balance is {starkgate_balance}")
            res = await starkgate.balance(L1_CONTRACT_ADDRESS).call()
            assert res.result.balance == uint(starkgate_balance)

@pytest.mark.asyncio
async def test_depart_exceed_fleet_size(starknet, admiral, cargo_token, l2_keeper, user1):
    max_size = 2
    await l2_keeper.mint(cargo_token, user1, 100000)
    await user1.approve(cargo_token, admiral.contract_address, 100000)
    await l2_keeper.send_transaction(admiral.contract_address, 'set_max_fleet_size', calldata=[max_size])

    await user1.deposit_into_ship(admiral, 1000)
    await user1.depart(admiral, 1)
    res = await admiral.get_fleet_size().call()
    print(f"{res.result}")
    print("Departed ship 1")

    await user1.deposit_into_ship(admiral, 1000)
    await user1.depart(admiral, 2)
    res = await admiral.get_fleet_size().call()
    print(f"{res.result}")
    print("Departed ship 2")

    await user1.deposit_into_ship(admiral, 1000)
    with pytest.raises(Exception):
        print("Trying to depart ship 3")
        await user1.depart(admiral, 3)
        print("Departed 3")

    await starknet.send_message_to_l2(L1_CONTRACT_ADDRESS, admiral.contract_address, L1_HANDLER_SELECTOR, [1, 1000, 0, 50, 0, 42, 0])
    res = await admiral.get_fleet_size().call()
    print(f"{res.result}")

    print("Departing ship 3")
    await user1.depart(admiral, 3)
    print("Departed 3")


@pytest.mark.asyncio
async def test_depart_wrong_index(admiral, cargo_token, l2_keeper, user1):
    await l2_keeper.mint(cargo_token, user1, 2000)
    await user1.approve(cargo_token, admiral.contract_address, 5000)

    await user1.deposit_into_ship(admiral, 1000)

    with pytest.raises(Exception):
        await user1.depart(admiral, 5)

@pytest.mark.asyncio
async def test_depart_not_crew(admiral, cargo_token, l2_keeper, user1, user2):
    await l2_keeper.mint(cargo_token, user1, 2000)
    await user1.approve(cargo_token, admiral.contract_address, 5000)
    await user1.deposit_into_ship(admiral, 1000)

    with pytest.raises(Exception):
        await user2.depart(admiral, 1)

@pytest.mark.asyncio
async def test_depart_keeper(admiral, cargo_token, l2_keeper, user1):
    await l2_keeper.mint(cargo_token, user1, 2000)
    await user1.approve(cargo_token, admiral.contract_address, 5000)
    await user1.deposit_into_ship(admiral, 1000)

    await l2_keeper.depart(admiral, 1)

async def check_ship_details(admiral, total, contributor_count):
    print(f"Checking open ship {contributor_count} contributors with a total of {total}")
    res = await admiral.get_open_ship_status().call()
    assert res.result.ship_cargo == uint(total)
    assert len(res.result.crew) == contributor_count

    return res.result.ship_idx


async def check_ships_indices(admiral, oldest_idx: int, active_count: int):
    oldest_active_idx = await admiral.get_oldest_active_ship_idx().call()
    active_ships_count = await admiral.get_fleet_size().call()
    assert oldest_active_idx.result.ship_idx == oldest_idx
    assert active_ships_count.result.count == active_count
