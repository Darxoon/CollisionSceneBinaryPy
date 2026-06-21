from array import array
from math import degrees
import numpy as np
import gltflib
from CsbFile import CsbFile
from Triangle import Triangle

# eff = material.Effect("effect0", [], "phong", diffuse=(1.0, 1.0, 1.0, 1.0), double_sided=False)
csb: CsbFile

def SetupMaterial(iomodel, ioscene, attribute: int, flag: int, identifiers: list[int] = None):
    global eff
    if identifiers is None:
        name = f"MAT{attribute}_FLAG{flag}"
    else:
        #print(identifiers)
        name = f"MAT{attribute}_FLAG{flag}_ID-A{identifiers[0]}_ID-B{identifiers[1]}"
    
    mat = material.Material(name, name, eff)
    matnode = scene.MaterialNode(symbol=name, target=mat, inputs=())
    if not [None for x in ioscene.nodes if type(x) is scene.MaterialNode and x.symbol == matnode.symbol]: # if matnode isn't in nodelist:
        ioscene.nodes.append(matnode)
        iomodel.materials.append(mat)
    return matnode

def SetupMesh(iomodel: gltflib.GLTFModel, buffer: bytearray, name: str, triangles: list[Triangle], positions: list[list[float]]) -> int:
    if not triangles:
        return None
    
    indices: array[int] = array('H')
    
    print(name)
    # print(positions)
    print([(positions[tri.A], positions[tri.B], positions[tri.C]) for tri in triangles[1:2]])
    print()
    
    for tri in triangles:
        indices.append(tri.A)
        indices.append(tri.B)
        indices.append(tri.C)
    
    # indices
    indices_accessor = len(iomodel.accessors)
    indices_bytes = indices.tobytes()
    iomodel.accessors.append(gltflib.Accessor(
        bufferView=len(iomodel.bufferViews),
        byteOffset=0,
        componentType=gltflib.ComponentType.UNSIGNED_SHORT.value,
        count=len(indices),
        type=gltflib.AccessorType.SCALAR.value,
        min=[min(indices)],
        max=[max(indices)],
    ))
    iomodel.bufferViews.append(gltflib.BufferView(
        buffer=0,
        byteOffset=len(buffer),
        byteLength=len(indices_bytes),
        target=gltflib.BufferTarget.ELEMENT_ARRAY_BUFFER.value,
    ))
    buffer.extend(indices_bytes)
    
    # vertices
    vertices_accessor = len(iomodel.accessors)
    vertices_bytes = np.array(positions, dtype=np.float32).ravel().tobytes()
    
    iomodel.accessors.append(gltflib.Accessor(
        bufferView=len(iomodel.bufferViews),
        byteOffset=0,
        componentType=gltflib.ComponentType.FLOAT.value,
        count=len(positions),
        type=gltflib.AccessorType.VEC3.value,
        min=[min(pos[0] for pos in positions), min(pos[1] for pos in positions), min(pos[2] for pos in positions)],
        max=[max(pos[0] for pos in positions), max(pos[1] for pos in positions), max(pos[2] for pos in positions)],
    ))
    iomodel.bufferViews.append(gltflib.BufferView(
        buffer=0,
        byteOffset=len(buffer),
        byteLength=len(vertices_bytes),
        target=gltflib.BufferTarget.ARRAY_BUFFER.value,
    ))
    buffer.extend(vertices_bytes)
    
    # mesh
    mesh_index = len(iomodel.meshes)
    iomodel.meshes.append(gltflib.Mesh(primitives=[
        gltflib.Primitive(
            attributes=gltflib.Attributes(POSITION=vertices_accessor),
            indices=indices_accessor,
        ),
    ]))
    return mesh_index
    

def LoadNode(iomodel: gltflib.GLTFModel, node_list: list[gltflib.Node], node: CsbFile.Node, parent, repeat):
    global currentIdx
    index = node.ID
    #print(currentIdx)
    if not repeat:
        currentIdx += 1
    
    #print(index)
    
    #find the model, mesh or mobj that links to this to label it
    name = f"Node{currentIdx}"
    
    model = next((x for x in csb.Models if x.NodeIndex == index), None)
    
    if not model is None:
        model.AbsoluteIndex = currentIdx - 1
    
    else:
        obj = next((x for x in csb.Objects if x.NodeIndex == index), None)
        
        if not obj is None:
            obj.AbsoluteIndex = currentIdx - 1
        
        elif len(csb.Models[0].Meshes) > 0 :
            mesh = next((x for x in csb.Models[0].Meshes if x.NodeIndex == index), None)
            if not mesh is None:
                mesh.AbsoluteIndex = currentIdx - 1
                name = f"{mesh.Name}"
    
    bone = gltflib.Node(name=name, children=[])
    
    node_list.append(bone)
    
    if parent is not None:
        parent.children.append(len(iomodel.nodes))
    
    iomodel.nodes.append(bone)
    
    #print(node.NumChildren)
    if csb.OldParenting:
        startIdx = currentIdx
        while currentIdx < (startIdx + node.NumChildren):
            LoadNode(iomodel, node_list, csb.Nodes[currentIdx], bone, False)
    else:
        for i in range(node.NumChildren):
            LoadNode(iomodel, node_list, csb.Nodes[currentIdx], bone, False)
    
def Export(csb_in: CsbFile, filePath):
    global csb
    
    csb = csb_in
    iomodel: gltflib.GLTFModel = gltflib.GLTFModel(
        asset=gltflib.Asset(version='2.0'),
        scenes=[gltflib.Scene(nodes=[0])],
        nodes=[],
        meshes=[], #[gltflib.Mesh(primitives=[gltflib.Primitive(attributes=gltflib.Attributes(POSITION=0))])],
        bufferViews=[],
        accessors=[],
        # buffers=[gltflib.Buffer(byteLength=bytelen, uri='vertices.bin')],
        # bufferViews=[gltflib.BufferView(buffer=0, byteOffset=0, byteLength=bytelen, target=gltflib.BufferTarget.ARRAY_BUFFER.value)],
        # accessors=[gltflib.Accessor(
        #     bufferView=0,
        #     byteOffset=0,
        #     componentType=gltflib.ComponentType.FLOAT.value,
        #     count=len(vertices),
        #     type=gltflib.AccessorType.VEC3.value,
        #     min=mins,
        #     max=maxs,
        # )]
    )
    
    buffer = bytearray()
    
    # iomodel.effects.append(eff)
    
    
    #node tree
    
    global currentIdx
    currentIdx = 0
    
    node_list: list[gltflib.Node] = []
    
    #print([x.Name for x in csb.Nodes])
    #print()
    while len(node_list) < len(csb.Nodes):
        LoadNode(iomodel, node_list, csb.Nodes[currentIdx], None, False)
    
    for obj in csb.Objects:
        obj: CsbFile.CollisionObject = obj
        type = "MAPOBJ_SPHERE" if obj.IsSphere else "MAPOBJ_BOX"
        
        # mat = SetupMaterial(iomodel, ioscene, 0, obj.ColFlag, [obj.Identifier1, obj.Identifier2])
        
        #Add meshes as map objects
        # iomesh, iomeshnode = SetupMesh(iomodel, f"{type}_{obj.Name}", mat, [], [])
        # iomodel.geometries.append(iomesh)
        node: gltflib.Node = node_list[obj.AbsoluteIndex]
        node.name = f'{type}_{obj.Name}'
        node.translation = list(obj.Point1)
        node.scale = [*obj.Size]
        # node.children.append(scene.RotateTransform(0, 0, 1, degrees(obj.Rotation[2])))
        # node.children.append(scene.RotateTransform(0, 1, 0, degrees(obj.Rotation[1])))
        # node.children.append(scene.RotateTransform(1, 0, 0, degrees(obj.Rotation[0])))
        
        # if obj.IsSphere:
        #     node_list[obj.AbsoluteIndex].children[-1] = scene.ScaleTransform(obj.Radius, obj.Radius, obj.Radius)
    
    for idx, model in enumerate(csb.Models):
        model: CsbFile.Model = model
        if len(model.Meshes) > 0:
            
            for mesh in model.Meshes:
                mesh: CsbFile.Mesh = mesh
                # mat = SetupMaterial(iomodel, ioscene, mesh.MaterialAttribute, mesh.ColFlag)
                
                mesh_index = SetupMesh(iomodel, buffer, mesh.Name, mesh.Triangles, mesh.Positions)
                node: gltflib.Node = node_list[mesh.AbsoluteIndex]
                node.mesh = mesh_index
            
        elif len(model.Triangles) > 0:
            # mat = SetupMaterial(iomodel, ioscene, model.MaterialAttribute, model.ColFlag)
            
            mesh_index = SetupMesh(iomodel, buffer, model.Name, model.Triangles, model.Positions)
            node: gltflib.Node = node_list[model.AbsoluteIndex]
            node.name = f'MODELSPLIT_{model.Name}'
            node.mesh = mesh_index
            
            if node.translation is not None:
                node.translation[0] += model.Translate[0]
                node.translation[1] += model.Translate[1]
                node.translation[2] += model.Translate[2]
            else:
                node.translation = [*model.Translate]
            
            # node.children.append(scene.RotateTransform(0, 0, 1, degrees(model.Rotation[2])))
            # node.children.append(scene.RotateTransform(0, 1, 0, degrees(model.Rotation[1])))
            # node.children.append(scene.RotateTransform(1, 0, 0, degrees(model.Rotation[0])))
    
    iomodel.buffers = [gltflib.Buffer(byteLength=len(buffer), uri='vertices.bin')]
    resource = gltflib.FileResource('vertices.bin', data=buffer)
    gltf = gltflib.GLTF(model = iomodel, resources=[resource])
    gltf.export(filePath)
    