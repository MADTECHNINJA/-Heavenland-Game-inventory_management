from django.db import models


class InventoryItem(models.Model):
    username = models.CharField(max_length=32, db_index=True)
    item_id = models.IntegerField()
    description = models.CharField(max_length=64)
    fbx = models.CharField(max_length=64)
    ue_reference = models.CharField(max_length=64)


class Parcel(models.Model):
    username = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    location_x = models.DecimalField(max_digits=20, decimal_places=12, blank=True, null=True)
    location_y = models.DecimalField(max_digits=20, decimal_places=12, blank=True, null=True)
    building_id = models.BigIntegerField(null=True, blank=True)
    thumbnail = models.CharField(max_length=256, blank=True, null=True)
