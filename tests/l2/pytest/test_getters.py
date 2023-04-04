import pytest

from open_zeppelin.utils import (str_to_felt, uint)
from conftest import ShipStatus


class TestGetAllActiveRides:

    @pytest.mark.asyncio
    async def test_finalize_enough_balance(self, admiral, cargo_token, l2_keeper, user1):
        await l2_keeper.mint(cargo_token, user1, 5000)
        await user1.approve(cargo_token, admiral.contract_address, 5000)

        # Deposit & depart
        await user1.deposit_into_ship(admiral, 50)
        await user1.depart(admiral, 1)

        # don't deposit & depart
        await l2_keeper.depart(admiral, 2)

        # Deposit & depart
        await user1.deposit_into_ship(admiral, 60)
        await l2_keeper.depart(admiral, 3)

        await user1.deposit_into_ship(admiral, 20)

        res = await admiral.get_fleet().call()
        print(f">>>>>>> {res.result.ships}")
        assert len(res.result.ships) == 4
        assert res.result.start_idx == 1
        check_ship(res.result.ships[0], ShipStatus.AT_SEA, 50, 1)
        check_ship(res.result.ships[1], ShipStatus.AT_SEA, 0, 0)
        check_ship(res.result.ships[2], ShipStatus.AT_SEA, 60, 1)
        check_ship(res.result.ships[3], ShipStatus.OPEN, 20, 1)

        res = await admiral.get_balances(user1.contract_address).call()
        print(f">>>>>> {res.result}")
        assert uint(4870) == res.result.cargo_token_balance
        assert uint(0) == res.result.loot_token_balance

        assert 3 == len(res.result.cargo)
        assert res.result.cargo[0].ship_idx == 4
        assert res.result.cargo[0].amount == uint(20)
        assert res.result.cargo[1].ship_idx == 3
        assert res.result.cargo[1].amount == uint(60)
        assert res.result.cargo[2].ship_idx == 1
        assert res.result.cargo[2].amount == uint(50)



    @pytest.mark.asyncio
    async def test_get_metadata(self, admiral, cargo_token, l2_keeper, user1):
        await l2_keeper.mint(cargo_token, user1, 5000)
        await user1.approve(cargo_token, admiral.contract_address, 5000)

        res = await admiral.get_metadata().call()
        print(f">>>>>>> {res.result}")

        assert str_to_felt("PT") == res.result.cargo_token.symbol
        assert str_to_felt("PoolingToken") == res.result.cargo_token.name
        assert 18 == res.result.cargo_token.decimals

        assert str_to_felt("RT") == res.result.loot_token.symbol
        assert str_to_felt("PayoutToken") == res.result.loot_token.name
        assert 18 == res.result.loot_token.decimals

        assert res.result.min_deposit == uint(0)
        assert res.result.max_fleet_size == 20

def check_ship(ship, status: ShipStatus, cargo, crew):
    assert ship.status == status.value
    assert ship.cargo == uint(cargo)
    assert ship.crew == crew
