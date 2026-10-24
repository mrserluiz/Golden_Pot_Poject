package br.com.ethercraft.goldenpot;
import org.geysermc.geyser.api.GeyserApi;
import org.geysermc.geyser.api.event.EventRegistrar;
import org.geysermc.geyser.api.event.lifecycle.*;
import org.geysermc.geyser.api.block.custom.CustomBlockData;
import org.geysermc.geyser.api.block.custom.component.*;
import org.geysermc.geyser.api.item.custom.v2.*;
import org.geysermc.geyser.api.item.custom.v2.component.geyser.*;
import org.geysermc.geyser.api.util.Identifier;
import org.geysermc.geyser.api.pack.*;
final class BedrockBridge {
 private final GoldenPotGen plugin;
 private EventRegistrar owner;
 private GeyserApi api;
 volatile boolean blocks,items,pack;
 BedrockBridge(GoldenPotGen p){plugin=p;}
 void attach(){
  api=GeyserApi.api();if(api==null)throw new IllegalStateException("Geyser API unavailable during onLoad");
  owner=EventRegistrar.of(plugin);
  api.eventBus().subscribe(owner,GeyserDefineResourcePacksEvent.class,event->{
   var path=plugin.getDataFolder().toPath().resolve("generated/EtherTexture-Bedrock-GoldenPotGen.mcpack");
   try {
    var generated=ResourcePack.create(PackCodec.path(path));
    // Replace only the same official pack UUID in the runtime list; never delete source packs.
    event.unregister(generated.uuid());event.register(generated);pack=true;
   }catch(RuntimeException ex){plugin.getLogger().severe("Bedrock pack registration failed: "+ex);}
  });
  api.eventBus().subscribe(owner,GeyserDefineCustomBlocksEvent.class,event->{
   if(!plugin.experimental())return;
   try{
    var material=MaterialInstance.builder().texture("gpg_ambrosio_ore").renderMethod("opaque").faceDimming(true).ambientOcclusion(true).build();
    var components=CustomBlockComponents.builder().displayName("Minério de Ambrósio").unitCube(true).materialInstance("*",material).destructibleByMining(1.0f).build();
    var block=CustomBlockData.builder().name("gpg_ambrosio_ore").components(components).includedInCreativeInventory(false).build();
    event.register(block);event.registerOverride(Resources.STATE,block.defaultBlockState());blocks=true;
   }catch(RuntimeException ex){plugin.getLogger().severe("Geyser block registration failed: "+ex);}
  });
  api.eventBus().subscribe(owner,GeyserDefineCustomItemsEvent.class,event->{
   if(!plugin.experimental())return;
   try{
    var definition=CustomItemDefinition.builder(Identifier.of("goldenpot:ambrosio_ore"),Identifier.of("goldenpot:ambrosio_ore"))
     .displayName("Minério de Ambrósio")
     .bedrockOptions(CustomItemBedrockOptions.builder().icon("gpg_ambrosio_ore"))
     .component(GeyserItemDataComponents.BLOCK_PLACER,GeyserBlockPlacer.of(Identifier.of("geyser_custom:gpg_ambrosio_ore"),true))
     .build();
    event.register(Identifier.of("minecraft:note_block"),definition);items=true;
   }catch(RuntimeException ex){plugin.getLogger().severe("Geyser item registration failed: "+ex);}
  });
 }
 void close(){if(api!=null&&owner!=null)api.eventBus().unregisterAll(owner);}
}
